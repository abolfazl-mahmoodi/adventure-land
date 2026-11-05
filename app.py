import os
import re
import secrets
import time
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import dao
import week_time
import quest_logic

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

AVATAR_UPLOAD_FOLDER = os.path.join(app.static_folder, "images", "avatars")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
# I require at least 8 characters, one uppercase letter, one number, and one symbol.

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.email = row["email"]
        self.name = row["name"]
        self.surname = row["surname"]
        self.birthdate = row["birthdate"]
        self.role = row["role"]
        self.avatar_filename = row["avatar_filename"]
        self.bio = row["bio"]
        self.notify_opt_in = bool(row["notify_opt_in"])

    @property
    def is_guildmaster(self):
        return self.role == "guildmaster"

    @property
    def is_adventurer(self):
        return self.role == "adventurer"


@login_manager.user_loader
def load_user(user_id):
    row = dao.get_user_by_id(user_id)
    return User(row) if row else None


def adventurer_required(view_func):
    from functools import wraps

    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_adventurer:
            flash("That action is only available to adventurers.", "warning")
            return redirect(url_for("index"))
        return view_func(*args, **kwargs)

    return wrapped


def guildmaster_required(view_func):
    from functools import wraps

    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_guildmaster:
            flash("That page is only available to the Guild Master.", "warning")
            return redirect(url_for("index"))
        return view_func(*args, **kwargs)

    return wrapped

def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_avatar(file_storage, username):
    """I check and save an uploaded profile picture."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_image(file_storage.filename):
        return None
    ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    filename = f"{secure_filename(username)}_{int(time.time())}.{ext}"
    file_storage.save(os.path.join(AVATAR_UPLOAD_FOLDER, filename))
    return filename


def get_now():
    """I get the current day and time from the simulated clock."""
    row = dao.get_simulated_now()
    return row["current_day"], row["current_time_hhmm"]


def parse_hhmm(value):
    """I convert an HTML time into minutes after midnight."""
    try:
        parsed = datetime.strptime(value or "", "%H:%M")
    except (TypeError, ValueError):
        return None
    return parsed.hour * 60 + parsed.minute


def companion_data_from_form(places):
    """I read and check the companion information from the form."""
    if places != 2:
        return {"name": None, "surname": None, "birthdate": None, "email": None, "role_name": None}, None

    data = {
        "name": request.form.get("companion_name", "").strip(),
        "surname": request.form.get("companion_surname", "").strip(),
        "birthdate": request.form.get("companion_birthdate", "").strip(),
        "email": request.form.get("companion_email", "").strip().lower() or None,
        "role_name": request.form.get("companion_role", "").strip(),
    }
    if not data["name"] or len(data["name"]) > 50:
        return data, "Companion first name is required and must be 50 characters or fewer."
    if not data["surname"] or len(data["surname"]) > 50:
        return data, "Companion surname is required and must be 50 characters or fewer."
    try:
        birthdate = datetime.strptime(data["birthdate"], "%Y-%m-%d").date()
        if birthdate > datetime.now().date():
            return data, "Companion birthdate cannot be in the future."
    except ValueError:
        return data, "Please enter a valid companion birthdate."
    if data["email"] and (len(data["email"]) > 254 or not EMAIL_PATTERN.fullmatch(data["email"])):
        return data, "Please enter a valid companion email address or leave it empty."
    return data, None


@app.context_processor
def inject_globals():
    """I make these common values available in every template."""
    return {
        "guild_name": "Adventure Land",
        "guild_tagline": "Where your wildest ideas become our greatest quests",
        "today_iso": datetime.now().date().isoformat(),
    }


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        name = request.form.get("name", "").strip()
        surname = request.form.get("surname", "").strip()
        birthdate = request.form.get("birthdate", "").strip() or None
        notify_opt_in = 1 if request.form.get("notify_opt_in") else 0
        avatar_file = request.files.get("avatar")

        errors = {}

        if not USERNAME_PATTERN.fullmatch(username):
            errors["username"] = "Use 3–20 letters, numbers, or underscores only."
        elif dao.username_exists(username):
            errors["username"] = "This username is already taken — please choose another."

        if not EMAIL_PATTERN.fullmatch(email) or len(email) > 254:
            errors["email"] = "Please enter a valid email address."
        elif dao.email_exists(email):
            errors["email"] = "An account with this email already exists."

        if not name:
            errors["name"] = "Please enter your first name."
        elif len(name) > 50:
            errors["name"] = "First name must be 50 characters or fewer."
        if not surname:
            errors["surname"] = "Please enter your surname."
        elif len(surname) > 50:
            errors["surname"] = "Surname must be 50 characters or fewer."

        if birthdate:
            try:
                parsed_birthdate = datetime.strptime(birthdate, "%Y-%m-%d").date()
                if parsed_birthdate > datetime.now().date():
                    errors["birthdate"] = "Birthdate cannot be in the future."
            except ValueError:
                errors["birthdate"] = "Please enter a valid birthdate."

        if not PASSWORD_PATTERN.match(password):
            errors["password"] = (
                "Password must be at least 8 characters and include "
                "one uppercase letter, one number, and one symbol."
            )
        elif password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if avatar_file and avatar_file.filename and not allowed_image(avatar_file.filename):
            errors["avatar"] = "Image must be a .jpg, .jpeg, .png, .gif, or .webp file."

        if errors:
            return render_template(
                "signup.html",
                form_data=request.form,
                errors=errors,
            ), 400

        avatar_filename = save_avatar(avatar_file, username)

        user_id = dao.create_user(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            surname=surname,
            birthdate=birthdate,
            role="adventurer",
            avatar_filename=avatar_filename,
            notify_opt_in=notify_opt_in,
        )
        user_row = dao.get_user_by_id(user_id)
        login_user(User(user_row))
        flash(f"Welcome to Adventure Land, {name}!", "success")
        return redirect(url_for("index"))

    return render_template("signup.html", form_data={}, errors={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_row = dao.get_user_by_username(identifier) or dao.get_user_by_email(identifier.lower())

        if user_row is None:
            flash("No account was found with that username or email.", "danger")
            return render_template("login.html", form_data=request.form, errors={}), 400

        if not check_password_hash(user_row["password_hash"], password):
            flash("The password is incorrect. Please try again.", "danger")
            return render_template("login.html", form_data=request.form, errors={}), 400

        login_user(User(user_row))
        flash(f"Welcome back, {user_row['name']}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html", form_data={}, errors={})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/user/<int:user_id>")
def user_profile(user_id):
    profile_user = dao.get_user_by_id(user_id)
    if profile_user is None:
        flash("That user could not be found.", "danger")
        return redirect(url_for("quest_board"))

    created_quests = None
    adventurer_activity = None
    if profile_user["role"] == "guildmaster":
        created_quests = dao.get_quests_created_by(user_id)
    else:
        participations = dao.get_participations_for_adventurer(user_id)
        adventurer_activity = {
            "session_count": len(participations),
            "reserved_places": sum(p["places_reserved"] for p in participations),
            "roles": sorted({p["role_name"] for p in participations}),
        }

    return render_template(
        "user_profile.html",
        profile_user=profile_user,
        created_quests=created_quests,
        adventurer_activity=adventurer_activity,
    )


@app.route("/")
def root():
    return redirect(url_for("index"))


@app.route("/home")
def index():
    days = request.args.getlist("day")
    quest_types = request.args.getlist("quest_type")
    difficulties = request.args.getlist("difficulty")
    roles_selected = request.args.getlist("role")
    all_sessions = dao.get_all_sessions_with_details(
        days=days,
        quest_types=quest_types,
        difficulties=difficulties,
        roles=roles_selected,
    )

    return render_template(
        "home.html",
        locations=dao.get_all_locations(),
        guild_stats=dao.get_guild_stats(),
        experienced_adventurers=dao.get_adventurer_leaderboard(limit=3),
        recent_comments=dao.get_recent_comments(limit=3),
        sessions=all_sessions[:SESSIONS_PER_PAGE],
        total_count=len(all_sessions),
        days_options=week_time.DAY_ORDER,
        quest_types_options=dao.get_used_quest_types(),
        difficulties_options=dao.get_used_difficulties(),
        roles_options=dao.get_all_roles(),
        selected={"day": days, "quest_type": quest_types, "difficulty": difficulties, "role": roles_selected},
    )

SESSIONS_PER_PAGE = 4

@app.route("/quests")
def quest_board():
    days = request.args.getlist("day")
    quest_types = request.args.getlist("quest_type")
    difficulties = request.args.getlist("difficulty")
    roles_selected = request.args.getlist("role")
    show_all = request.args.get("show") == "all"

    all_sessions = dao.get_all_sessions_with_details(
        days=days, quest_types=quest_types, difficulties=difficulties, roles=roles_selected
    )
    sessions = all_sessions if show_all else all_sessions[:SESSIONS_PER_PAGE]
    has_more = not show_all and len(all_sessions) > SESSIONS_PER_PAGE

    return render_template(
        "quest_board.html",
        sessions=sessions,
        total_count=len(all_sessions),
        has_more=has_more,
        days_options=week_time.DAY_ORDER,
        quest_types_options=dao.get_used_quest_types(),
        difficulties_options=dao.get_used_difficulties(),
        roles_options=dao.get_all_roles(),
        selected={"day": days, "quest_type": quest_types, "difficulty": difficulties, "role": roles_selected},
    )

@app.route("/locations")
def locations():
    all_locations = dao.get_all_locations()
    locations_with_quests = []
    for loc in all_locations:
        locations_with_quests.append({"location": loc, "quests": dao.get_quests_at_location(loc["id"])})
    return render_template("locations.html", locations_with_quests=locations_with_quests)


@app.route("/rules")
def rules():
    return render_template(
        "rules.html",
        roles=dao.get_all_roles(),
        max_sessions=quest_logic.MAX_SESSIONS_PER_WEEK,
        max_places=quest_logic.MAX_PLACES_PER_JOIN,
        modify_cutoff_hours=week_time.MODIFY_CUTOFF_MINUTES // 60,
    )


@app.route("/heroes")
def heroes():
    return render_template(
        "heroes.html",
        core_characters=dao.get_core_characters(),
        bonus_characters=dao.get_bonus_characters(),
    )

@app.route("/tutorial")
def tutorial():
    return render_template(
        "tutorial.html",
        core_characters=dao.get_core_characters(),
        bonus_characters=dao.get_bonus_characters(),
        locations=dao.get_all_locations(),
    )

@app.route("/session/<int:session_id>")
def session_detail(session_id):
    session = dao.get_session_by_id(session_id)
    if session is None:
        flash("That quest session could not be found.", "danger")
        return redirect(url_for("quest_board"))

    availability = dao.get_role_availability(session_id)
    is_past = quest_logic.session_is_in_the_past(session["day"], session["start_time"])
    core_characters = dao.get_core_characters()
    bonus_character = dao.get_bonus_character_for_quest_type(session["quest_type_id"])
    role_characters = {character["title"]: character for character in core_characters}
    if bonus_character:
        role_characters[bonus_character["title"]] = bonus_character
    reservation_mode = request.args.get("reservation", "solo")
    if reservation_mode not in ("solo", "companion"):
        reservation_mode = "solo"
    now_row = dao.get_simulated_now()
    minutes_to_start = week_time.minutes_until(
        session["day"], session["start_time"], now_row["current_day"], now_row["current_time_hhmm"]
    )
    registration_countdown = None
    if minutes_to_start > 0:
        registration_countdown = week_time.format_time_until(
            session["day"], session["start_time"], now_row["current_day"], now_row["current_time_hhmm"]
        ).removeprefix("Starts in ")

    my_participation = None
    if current_user.is_authenticated and current_user.is_adventurer:
        my_participation = dao.get_participation(session_id, current_user.id)

    return render_template(
        "session_detail.html",
        session=session,
        availability=availability,
        roles=dao.get_roles_for_session(session["id"]),
        is_past=is_past,
        my_participation=my_participation,
        core_characters=core_characters,
        bonus_character=bonus_character,
        role_characters=role_characters,
        reservation_mode=reservation_mode,
        registration_countdown=registration_countdown,
        comments=dao.get_comments_for_quest(session["quest_id"]),
    )


@app.route("/session/<int:session_id>/comment", methods=["POST"])
@login_required
def post_comment(session_id):
    session = dao.get_session_by_id(session_id)
    if session is None:
        flash("That quest session could not be found.", "danger")
        return redirect(url_for("quest_board"))

    text = request.form.get("comment_text", "").strip()
    if not text:
        flash("Comment can't be empty.", "danger")
    elif len(text) > 1000:
        flash("Comment is too long (max 1000 characters).", "danger")
    else:
        dao.create_comment(session["quest_id"], current_user.id, text)
        flash("Comment posted.", "success")

    return redirect(url_for("session_detail", session_id=session_id))


@app.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = dao.get_comment_by_id(comment_id)
    if comment is None:
        flash("Comment not found.", "danger")
        return redirect(request.referrer or url_for("quest_board"))

    if comment["user_id"] != current_user.id:
        flash("You can only delete your own comments.", "warning")
        return redirect(request.referrer or url_for("quest_board"))

    # I return to a session page that belongs to this quest.
    session_id = dao.get_first_session_id_for_quest(comment["quest_id"])
    dao.delete_comment(comment_id)
    flash("Comment deleted.", "info")
    return redirect(url_for("session_detail", session_id=session_id) if session_id else url_for("quest_board"))


@app.route("/session/<int:session_id>/join", methods=["POST"])
@adventurer_required
def join_session(session_id):
    role_name = request.form.get("role")
    try:
        places = int(request.form.get("places", 1))
    except ValueError:
        places = 0

    companion, companion_error = companion_data_from_form(places)
    if companion_error:
        flash(companion_error, "danger")
        return redirect(url_for("session_detail", session_id=session_id))

    ok, error = quest_logic.can_join_session(
        session_id, current_user.id, role_name, places, companion["role_name"]
    )
    if not ok:
        flash(error, "danger")
        return redirect(url_for("session_detail", session_id=session_id))

    role = dao.get_role_by_name(role_name)
    companion_role = dao.get_role_by_name(companion["role_name"]) if companion["role_name"] else None
    dao.create_participation(
        session_id, current_user.id, role["id"], places,
        companion_name=companion["name"], companion_surname=companion["surname"],
        companion_birthdate=companion["birthdate"], companion_email=companion["email"],
        companion_role_id=companion_role["id"] if companion_role else None,
    )
    flash("You've joined the quest session!", "success")
    return redirect(url_for("session_detail", session_id=session_id))


@app.route("/profile")
@login_required
def profile():
    if current_user.is_guildmaster:
        quests_with_sessions = dao.get_quests_with_sessions_for_guildmaster(current_user.id)
        stats_by_session_id = {}
        participants_by_session_id = {}
        session_count = 0
        participation_count = 0
        reserved_places = 0

        for entry in quests_with_sessions:
            for item in entry["sessions"]:
                session_id = item["session"]["id"]
                stats = dao.get_session_stats(session_id)
                participants = dao.get_participants_for_session(session_id)
                stats_by_session_id[session_id] = stats
                participants_by_session_id[session_id] = participants
                session_count += 1
                participation_count += len(participants)
                reserved_places += stats["total_reserved"]

        return render_template(
            "guildmaster_profile.html",
            quests_with_sessions=quests_with_sessions,
            stats_by_session_id=stats_by_session_id,
            participants_by_session_id=participants_by_session_id,
            quest_count=len(quests_with_sessions),
            session_count=session_count,
            participation_count=participation_count,
            reserved_places=reserved_places,
        )

    participations = dao.get_participations_for_adventurer(current_user.id)
    now_row = dao.get_simulated_now()

    enriched = []
    for p in participations:
        modifiable = week_time.is_participation_modifiable(
            p["day"], p["start_time"], now_row["current_day"], now_row["current_time_hhmm"]
        )
        time_until = week_time.format_time_until(
            p["day"], p["start_time"], now_row["current_day"], now_row["current_time_hhmm"]
        )
        enriched.append({"participation": p, "modifiable": modifiable, "time_until": time_until})

    return render_template(
        "profile.html",
        participations=enriched,
        session_count=len(participations),
        max_sessions=quest_logic.MAX_SESSIONS_PER_WEEK,
    )


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    user_row = dao.get_user_by_id(current_user.id)
    errors = {}

    if request.method == "POST":
        action = request.form.get("action", "profile")

        if action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            if not check_password_hash(user_row["password_hash"], current_password):
                errors["current_password"] = "Current password is incorrect."
            if not PASSWORD_PATTERN.fullmatch(new_password):
                errors["new_password"] = (
                    "Password must be at least 8 characters and include "
                    "one uppercase letter, one number, and one symbol."
                )
            elif new_password != confirm_password:
                errors["confirm_password"] = "Passwords do not match."
            if not errors:
                dao.update_user_profile(
                    current_user.id,
                    name=user_row["name"],
                    surname=user_row["surname"],
                    bio=user_row["bio"],
                    password_hash=generate_password_hash(new_password),
                )
                flash("Your password was updated.", "success")
                return redirect(url_for("profile"))
            form_data = dict(user_row)
        else:
            name = request.form.get("name", "").strip()
            surname = request.form.get("surname", "").strip()
            bio = request.form.get("bio", "").strip() or None
            avatar_file = request.files.get("avatar")

            if not name:
                errors["name"] = "Please enter your first name."
            elif len(name) > 50:
                errors["name"] = "First name must be 50 characters or fewer."
            if not surname:
                errors["surname"] = "Please enter your surname."
            elif len(surname) > 50:
                errors["surname"] = "Surname must be 50 characters or fewer."
            if bio and len(bio) > 500:
                errors["bio"] = "Bio must be 500 characters or fewer."
            if avatar_file and avatar_file.filename and not allowed_image(avatar_file.filename):
                errors["avatar"] = "Image must be a .jpg, .jpeg, .png, .gif, or .webp file."

            if not errors:
                avatar_filename = None
                if avatar_file and avatar_file.filename:
                    avatar_filename = save_avatar(avatar_file, current_user.username)
                dao.update_user_profile(
                    current_user.id,
                    name=name,
                    surname=surname,
                    bio=bio,
                    avatar_filename=avatar_filename,
                )
                flash("Your profile was updated.", "success")
                return redirect(url_for("profile"))
            form_data = request.form
    else:
        form_data = dict(user_row)

    response = render_template("edit_profile.html", form_data=form_data, errors=errors, user_row=user_row)
    return (response, 400) if request.method == "POST" else response


@app.route("/participation/<int:participation_id>/edit", methods=["GET", "POST"])
@adventurer_required
def edit_participation(participation_id):
    participation = dao.get_participation_by_id(participation_id)
    if participation is None or participation["adventurer_id"] != current_user.id:
        flash("Participation not found.", "danger")
        return redirect(url_for("profile"))

    session = dao.get_session_by_id(participation["quest_session_id"])

    if request.method == "POST":
        role_name = request.form.get("role")
        try:
            places = int(request.form.get("places", 1))
        except ValueError:
            places = 0

        companion, companion_error = companion_data_from_form(places)
        if companion_error:
            flash(companion_error, "danger")
            return redirect(url_for("edit_participation", participation_id=participation_id))

        ok, error = quest_logic.can_modify_participation(
            participation_id, current_user.id, role_name, places, companion["role_name"]
        )
        if not ok:
            flash(error, "danger")
            return redirect(url_for("edit_participation", participation_id=participation_id))

        role = dao.get_role_by_name(role_name)
        companion_role = dao.get_role_by_name(companion["role_name"]) if companion["role_name"] else None
        dao.update_participation(
            participation_id, role["id"], places,
            companion_name=companion["name"], companion_surname=companion["surname"],
            companion_birthdate=companion["birthdate"], companion_email=companion["email"],
            companion_role_id=companion_role["id"] if companion_role else None,
        )
        flash("Your participation was updated.", "success")
        return redirect(url_for("profile"))

    availability = dao.get_role_availability(session["id"])
    current_role = dao.get_role_by_id(participation["role_id"])
    current_companion_role = (
        dao.get_role_by_id(participation["companion_role_id"])
        if participation["companion_role_id"] else None
    )
    editable_availability = dict(availability)
    editable_availability[current_role["name"]] = editable_availability.get(current_role["name"], 0) + 1
    if current_companion_role:
        editable_availability[current_companion_role["name"]] = editable_availability.get(current_companion_role["name"], 0) + 1

    roles = dao.get_roles_for_session(session["id"])
    default_mode = "companion" if participation["places_reserved"] == 2 else "solo"
    reservation_mode = request.args.get("reservation", default_mode)
    if reservation_mode not in ("solo", "companion"):
        reservation_mode = default_mode

    core_characters = dao.get_core_characters()
    bonus_character = dao.get_bonus_character_for_quest_type(session["quest_type_id"])
    role_characters = {character["title"]: character for character in core_characters}
    if bonus_character:
        role_characters[bonus_character["title"]] = bonus_character

    return render_template(
        "edit_participation.html",
        participation=participation,
        session=session,
        roles=roles,
        availability=availability,
        editable_availability=editable_availability,
        current_role=current_role,
        current_companion_role=current_companion_role,
        reservation_mode=reservation_mode,
        role_characters=role_characters,
    )


@app.route("/participation/<int:participation_id>/cancel", methods=["POST"])
@adventurer_required
def cancel_participation(participation_id):
    ok, error = quest_logic.can_cancel_participation(participation_id, current_user.id)
    if not ok:
        flash(error, "danger")
        return redirect(url_for("profile"))

    dao.delete_participation(participation_id)
    flash("Your participation was cancelled.", "info")
    return redirect(url_for("profile"))


@app.route("/guildmaster")
@guildmaster_required
def guildmaster_dashboard():
    quests_with_sessions = dao.get_quests_with_sessions_for_guildmaster(current_user.id)

    stats_by_session_id = {}
    participants_by_session_id = {}
    for entry in quests_with_sessions:
        for s in entry["sessions"]:
            sid = s["session"]["id"]
            stats_by_session_id[sid] = dao.get_session_stats(sid)
            participants_by_session_id[sid] = dao.get_participants_for_session(sid)

    now_row = dao.get_simulated_now()
    return render_template(
        "guildmaster_dashboard.html",
        quests_with_sessions=quests_with_sessions,
        stats_by_session_id=stats_by_session_id,
        participants_by_session_id=participants_by_session_id,
        now=now_row,
    )


@app.route("/guildmaster/quests/new", methods=["GET", "POST"])
@guildmaster_required
def new_quest():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        duration = request.form.get("duration_minutes", "").strip()
        quest_type_id = request.form.get("quest_type_id")
        difficulty_id = request.form.get("difficulty_id")
        description = request.form.get("description", "").strip()
        image_file = request.files.get("image")

        errors = {}
        if not title:
            errors["title"] = "Please enter a quest title."
        elif len(title) > 120:
            errors["title"] = "Quest title must be 120 characters or fewer."
        try:
            duration_val = int(duration)
            if duration_val <= 0:
                errors["duration_minutes"] = "Duration must be a positive number of minutes."
        except ValueError:
            errors["duration_minutes"] = "Duration must be a whole number of minutes."
        if not description:
            errors["description"] = "Please enter a short description."
        elif len(description) > 2000:
            errors["description"] = "Description must be 2000 characters or fewer."
        quest_type = dao.get_quest_type_by_id(quest_type_id) if quest_type_id else None
        if quest_type is None:
            errors["quest_type_id"] = "Please select a valid quest type."
        difficulty = dao.get_difficulty_by_id(difficulty_id) if difficulty_id else None
        if difficulty is None:
            errors["difficulty_id"] = "Please select a valid difficulty."
        if not image_file or image_file.filename == "":
            errors["image"] = "Please choose a promotional image for this quest."
        elif not allowed_image(image_file.filename):
            errors["image"] = "Image must be a .jpg, .jpeg, .png, .gif, or .webp file."

        if errors:
            return render_template(
                "quest_form.html",
                form_data=request.form,
                errors=errors,
                quest_types=dao.get_all_quest_types(),
                difficulties=dao.get_all_difficulties(),
            ), 400

        ext = secure_filename(image_file.filename).rsplit(".", 1)[1].lower()
        image_filename = f"{secure_filename(title.lower().replace(' ', '_'))}_{int(time.time())}.{ext}"
        image_file.save(os.path.join(app.static_folder, "images", "quests", image_filename))

        quest_id = dao.create_quest(
            guild_master_id=current_user.id,
            title=title,
            duration_minutes=duration_val,
            quest_type_id=quest_type_id,
            difficulty_id=difficulty_id,
            description=description,
            image_filename=image_filename,
        )
        flash(f'Quest "{title}" created. Now schedule its first session.', "success")
        return redirect(url_for("new_session", quest_id=quest_id))

    return render_template(
        "quest_form.html",
        form_data={},
        errors={},
        quest_types=dao.get_all_quest_types(),
        difficulties=dao.get_all_difficulties(),
    )


@app.route("/guildmaster/sessions/new", methods=["GET", "POST"])
@guildmaster_required
def new_session():
    preselected_quest_id = request.args.get("quest_id", type=int)

    if request.method == "POST":
        quest_id = request.form.get("quest_id")
        day = request.form.get("day")
        start_time = request.form.get("start_time")
        location_id = request.form.get("location_id")

        errors = {}
        quest = dao.get_quest_by_id(quest_id) if quest_id else None
        if quest is None:
            errors["quest_id"] = "Please select a quest."
        if day not in week_time.DAY_ORDER:
            errors["day"] = "Please select a valid day."
        if not start_time:
            errors["start_time"] = "Please choose a start time."
        start_minutes = parse_hhmm(start_time)
        if start_minutes is None:
            errors["start_time"] = "Please enter a valid time."
        location = dao.get_location_by_id(location_id) if location_id else None
        if location is None:
            errors["location_id"] = "Please select a location."

        if not errors:
            end_minutes = start_minutes + quest["duration_minutes"]
            if end_minutes > 24 * 60:
                errors["start_time"] = "A quest session must finish by midnight on the selected day."
            else:
                end_time = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"
        if not errors:
            if dao.location_time_conflict_exists(day, start_time, end_time, int(location_id)):
                errors["start_time"] = (
                    f"{location['name']} already has a quest session that overlaps this time on {day}."
                )

        if errors:
            return render_template(
                "session_form.html",
                form_data=request.form,
                errors=errors,
                quests=dao.get_all_quests_with_details(),
                days=week_time.DAY_ORDER,
                locations=dao.get_all_locations(),
                mode="create",
            ), 400

        dao.create_session(quest_id, day, start_time, location_id)
        flash("Quest session scheduled!", "success")
        return redirect(url_for("guildmaster_dashboard"))

    return render_template(
        "session_form.html",
        form_data={"quest_id": preselected_quest_id} if preselected_quest_id else {},
        errors={},
        quests=dao.get_all_quests_with_details(),
        days=week_time.DAY_ORDER,
        locations=dao.get_all_locations(),
        mode="create",
    )


@app.route("/guildmaster/sessions/<int:session_id>/edit", methods=["GET", "POST"])
@guildmaster_required
def edit_session(session_id):
    session = dao.get_session_by_id(session_id)
    if session is None:
        flash("That quest session could not be found.", "danger")
        return redirect(url_for("guildmaster_dashboard"))

    if dao.session_has_participants(session_id):
        flash("This session already has participants and can no longer be modified.", "warning")
        return redirect(url_for("guildmaster_dashboard"))

    if request.method == "POST":
        day = request.form.get("day")
        start_time = request.form.get("start_time")
        location_id = request.form.get("location_id")

        errors = {}
        if day not in week_time.DAY_ORDER:
            errors["day"] = "Please select a valid day."
        if not start_time:
            errors["start_time"] = "Please choose a start time."
        start_minutes = parse_hhmm(start_time)
        if start_minutes is None:
            errors["start_time"] = "Please enter a valid time."
        location = dao.get_location_by_id(location_id) if location_id else None
        if location is None:
            errors["location_id"] = "Please select a location."

        if not errors:
            end_minutes = start_minutes + session["duration_minutes"]
            if end_minutes > 24 * 60:
                errors["start_time"] = "A quest session must finish by midnight on the selected day."
            else:
                end_time = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"
        if not errors:
            if dao.location_time_conflict_exists(day, start_time, end_time, int(location_id), exclude_session_id=session_id):
                errors["start_time"] = (
                    f"{location['name']} already has a quest session that overlaps this time on {day}."
                )

        if errors:
            return render_template(
                "session_form.html",
                form_data=request.form,
                errors=errors,
                quests=dao.get_all_quests_with_details(),
                days=week_time.DAY_ORDER,
                locations=dao.get_all_locations(),
                mode="edit",
                session=session,
            ), 400

        dao.update_session(session_id, day, start_time, location_id)
        flash("Quest session updated.", "success")
        return redirect(url_for("guildmaster_dashboard"))

    return render_template(
        "session_form.html",
        form_data={"day": session["day"], "start_time": session["start_time"], "location_id": session["location_id"]},
        errors={},
        quests=dao.get_all_quests_with_details(),
        days=week_time.DAY_ORDER,
        locations=dao.get_all_locations(),
        mode="edit",
        session=session,
    )


@app.route("/guildmaster/sessions/<int:session_id>/cancel", methods=["POST"])
@guildmaster_required
def cancel_session(session_id):
    if dao.session_has_participants(session_id):
        flash("This session already has participants and can no longer be cancelled.", "warning")
        return redirect(url_for("guildmaster_dashboard"))

    dao.delete_session(session_id)
    flash("Quest session cancelled.", "info")
    return redirect(url_for("guildmaster_dashboard"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
