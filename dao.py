"""I keep all database queries here so app.py stays easier to read."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "guild.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # I use column names such as row["username"].
    return conn


# I keep the user database functions in this section.

def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def get_user_by_username(username):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def username_exists(username):
    return get_user_by_username(username) is not None


def email_exists(email):
    return get_user_by_email(email) is not None


def create_user(username, email, password_hash, name, surname, birthdate, role,
                 avatar_filename=None, notify_opt_in=0):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO users
           (username, email, password_hash, name, surname, birthdate, role, avatar_filename, notify_opt_in)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (username, email, password_hash, name, surname, birthdate, role, avatar_filename, notify_opt_in),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_user_profile(user_id, name, surname, bio=None, password_hash=None, avatar_filename=None):
    """I update profile fields but keep the username and email unchanged."""
    fields = ["name = ?", "surname = ?", "bio = ?"]
    values = [name, surname, bio]
    if password_hash is not None:
        fields.append("password_hash = ?")
        values.append(password_hash)
    if avatar_filename is not None:
        fields.append("avatar_filename = ?")
        values.append(avatar_filename)
    values.append(user_id)

    conn = get_connection()
    conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_all_adventurers():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users WHERE role = 'adventurer' ORDER BY username").fetchall()
    conn.close()
    return rows


def get_adventurer_leaderboard(limit=4):
    """I rank adventurers by their sessions, places, and specialist roles."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT u.id, u.username, u.name, u.surname, u.avatar_filename,
                  COUNT(DISTINCT p.quest_session_id) AS session_count,
                  COALESCE(SUM(p.places_reserved), 0) AS reserved_places,
                  COUNT(DISTINCT CASE WHEN r.quest_type_id IS NOT NULL OR cr.quest_type_id IS NOT NULL
                                      THEN p.id END) AS specialist_count
           FROM users u
           LEFT JOIN participations p ON p.adventurer_id = u.id
           LEFT JOIN roles r ON r.id = p.role_id
           LEFT JOIN roles cr ON cr.id = p.companion_role_id
           WHERE u.role = 'adventurer'
           GROUP BY u.id
           ORDER BY session_count DESC, reserved_places DESC, specialist_count DESC, u.username
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_quests_created_by(guild_master_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT q.*, qt.name AS quest_type, d.name AS difficulty
           FROM quests q
           JOIN quest_types qt ON qt.id = q.quest_type_id
           JOIN difficulties d ON d.id = q.difficulty_id
           WHERE q.guild_master_id = ?
           ORDER BY q.title""",
        (guild_master_id,),
    ).fetchall()
    conn.close()
    return rows


def get_all_locations():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM locations ORDER BY name").fetchall()
    conn.close()
    return rows


def get_quests_for_location(location_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT DISTINCT q.*, qt.name AS quest_type, d.name AS difficulty
           FROM quests q
           JOIN quest_types qt ON qt.id = q.quest_type_id
           JOIN difficulties d ON d.id = q.difficulty_id
           JOIN quest_sessions qs ON qs.quest_id = q.id
           WHERE qs.location_id = ?
           ORDER BY q.title""",
        (location_id,),
    ).fetchall()
    conn.close()
    return rows


def get_all_quest_types():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM quest_types ORDER BY name").fetchall()
    conn.close()
    return rows


def get_quest_type_by_id(quest_type_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM quest_types WHERE id = ?", (quest_type_id,)).fetchone()
    conn.close()
    return row


def get_all_difficulties():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM difficulties ORDER BY id").fetchall()
    conn.close()
    return rows


def get_difficulty_by_id(difficulty_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM difficulties WHERE id = ?", (difficulty_id,)).fetchone()
    conn.close()
    return row


def get_used_quest_types():
    """I get only quest types that are currently used by a quest."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT DISTINCT qt.* FROM quest_types qt
           JOIN quests q ON q.quest_type_id = qt.id
           ORDER BY qt.name"""
    ).fetchall()
    conn.close()
    return rows


def get_used_difficulties():
    """I get only difficulty levels that are currently used by a quest."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT DISTINCT d.* FROM difficulties d
           JOIN quests q ON q.difficulty_id = d.id
           ORDER BY d.id"""
    ).fetchall()
    conn.close()
    return rows


def get_most_popular_quests(limit=6):
    """I order quests by their total number of reserved places."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT q.*, qt.name AS quest_type, d.name AS difficulty,
                  COALESCE(SUM(p.places_reserved), 0) AS total_reserved
           FROM quests q
           JOIN quest_types qt ON qt.id = q.quest_type_id
           JOIN difficulties d ON d.id = q.difficulty_id
           LEFT JOIN quest_sessions qs ON qs.quest_id = q.id
           LEFT JOIN participations p ON p.quest_session_id = qs.id
           GROUP BY q.id
           ORDER BY total_reserved DESC, q.title
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_first_session_id_for_quest(quest_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM quest_sessions WHERE quest_id = ? ORDER BY id LIMIT 1", (quest_id,)
    ).fetchone()
    conn.close()
    return row["id"] if row else None


def get_guild_stats():
    conn = get_connection()
    stats = {
        "total_quests": conn.execute("SELECT COUNT(*) FROM quests").fetchone()[0],
        "total_sessions": conn.execute("SELECT COUNT(*) FROM quest_sessions").fetchone()[0],
        "total_adventurers": conn.execute("SELECT COUNT(*) FROM users WHERE role = 'adventurer'").fetchone()[0],
        "total_reservations": conn.execute(
            "SELECT COALESCE(SUM(places_reserved), 0) FROM participations"
        ).fetchone()[0],
    }
    conn.close()
    return stats


def get_recent_comments(limit=3):
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, u.username, u.name, u.surname, u.avatar_filename, q.title AS quest_title,
                  q.id AS quest_id
           FROM quest_comments c
           JOIN users u ON u.id = c.user_id
           JOIN quests q ON q.id = c.quest_id
           ORDER BY c.created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_quest_types_with_sample():
    """I get each used quest type with an image and its session count."""
    conn = get_connection()
    types = conn.execute(
        """SELECT DISTINCT qt.id, qt.name FROM quest_types qt
           JOIN quests q ON q.quest_type_id = qt.id
           ORDER BY qt.name"""
    ).fetchall()

    result = []
    for t in types:
        sample = conn.execute(
            "SELECT image_filename FROM quests WHERE quest_type_id = ? LIMIT 1", (t["id"],)
        ).fetchone()
        count = conn.execute(
            """SELECT COUNT(*) FROM quest_sessions qs
               JOIN quests q ON q.id = qs.quest_id
               WHERE q.quest_type_id = ?""",
            (t["id"],),
        ).fetchone()[0]
        result.append({"id": t["id"], "name": t["name"], "image_filename": sample["image_filename"], "session_count": count})
    conn.close()
    return result


def get_quests_at_location(location_id):
    """I get the quests that have a session at the selected location."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT DISTINCT q.id, q.title, q.image_filename, qt.name AS quest_type, d.name AS difficulty
           FROM quests q
           JOIN quest_types qt ON qt.id = q.quest_type_id
           JOIN difficulties d ON d.id = q.difficulty_id
           JOIN quest_sessions qs ON qs.quest_id = q.id
           WHERE qs.location_id = ?
           ORDER BY q.title""",
        (location_id,),
    ).fetchall()
    conn.close()
    result = []
    for q in rows:
        result.append({"quest": q, "session_id": get_first_session_id_for_quest(q["id"])})
    return result


def get_all_roles():
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.*, qt.name AS quest_type_name
           FROM roles r
           LEFT JOIN quest_types qt ON qt.id = r.quest_type_id
           ORDER BY r.id"""
    ).fetchall()
    conn.close()
    return rows


def get_roles_for_session(session_id):
    """I get the basic roles and the specialist role for this session."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.*, qt.name AS quest_type_name
           FROM roles r
           LEFT JOIN quest_types qt ON qt.id = r.quest_type_id
           JOIN quest_sessions qs ON qs.id = ?
           JOIN quests q ON q.id = qs.quest_id
           WHERE r.quest_type_id IS NULL OR r.quest_type_id = q.quest_type_id
           ORDER BY r.id""",
        (session_id,),
    ).fetchall()
    conn.close()
    return rows

def get_core_characters():
    """I get the Warrior, Mage, and Healer characters in order."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, r.name AS role_name
           FROM characters c JOIN roles r ON r.id = c.role_id
           WHERE c.category = 'core'
           ORDER BY r.id"""
    ).fetchall()
    conn.close()
    return rows


def get_bonus_characters():
    """I get all specialist characters for the Heroes page."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, qt.name AS quest_type_name
           FROM characters c JOIN quest_types qt ON qt.id = c.quest_type_id
           WHERE c.category = 'bonus'
           ORDER BY qt.id"""
    ).fetchall()
    conn.close()
    return rows


def get_bonus_character_for_quest_type(quest_type_id):
    """I get the specialist character for one quest type."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM characters WHERE category = 'bonus' AND quest_type_id = ?",
        (quest_type_id,),
    ).fetchone()
    conn.close()
    return row



def get_simulated_now():
    conn = get_connection()
    row = conn.execute("SELECT current_day, current_time_hhmm FROM app_settings WHERE id = 1").fetchone()
    conn.close()
    return row


def get_all_quests_with_details():
    """I get every quest with its type, difficulty, and sessions."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT q.*, qt.name AS quest_type, d.name AS difficulty
           FROM quests q
           JOIN quest_types qt ON qt.id = q.quest_type_id
           JOIN difficulties d ON d.id = q.difficulty_id
           ORDER BY q.title"""
    ).fetchall()
    conn.close()
    return rows


def get_quest_by_id(quest_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT q.*, qt.name AS quest_type, d.name AS difficulty,
                  u.username AS creator_username, u.name AS creator_name, u.surname AS creator_surname
           FROM quests q
           JOIN quest_types qt ON qt.id = q.quest_type_id
           JOIN difficulties d ON d.id = q.difficulty_id
           JOIN users u ON u.id = q.guild_master_id
           WHERE q.id = ?""",
        (quest_id,),
    ).fetchone()
    conn.close()
    return row


def create_quest(guild_master_id, title, duration_minutes, quest_type_id, difficulty_id,
                  description, image_filename):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO quests
           (guild_master_id, title, duration_minutes, quest_type_id, difficulty_id, description, image_filename)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (guild_master_id, title, duration_minutes, quest_type_id, difficulty_id, description, image_filename),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id



DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_all_sessions_with_details(days=None, quest_types=None, difficulties=None, roles=None):
    """I get session details and apply all selected filters."""
    conn = get_connection()
    query = """
        SELECT qs.id, qs.day, qs.start_time, qs.quest_id,
               q.title, q.duration_minutes, q.image_filename, q.description,
               qt.name AS quest_type, d.name AS difficulty,
               l.name AS location
        FROM quest_sessions qs
        JOIN quests q ON q.id = qs.quest_id
        JOIN quest_types qt ON qt.id = q.quest_type_id
        JOIN difficulties d ON d.id = q.difficulty_id
        JOIN locations l ON l.id = qs.location_id
        WHERE 1=1
    """
    params = []
    if days:
        query += f" AND qs.day IN ({','.join('?' * len(days))})"
        params.extend(days)
    if quest_types:
        query += f" AND qt.name IN ({','.join('?' * len(quest_types))})"
        params.extend(quest_types)
    if difficulties:
        query += f" AND d.name IN ({','.join('?' * len(difficulties))})"
        params.extend(difficulties)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    rows = sorted(rows, key=lambda r: (DAY_ORDER.index(r["day"]), r["start_time"]))

    if roles:
        # I keep a session when at least one selected role still has space.
        rows = [
            r for r in rows
            if any(get_role_availability(r["id"]).get(role_name, 0) > 0 for role_name in roles)
        ]

    return rows


def get_session_by_id(session_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT qs.*, q.title, q.duration_minutes, q.description, q.image_filename, q.quest_type_id,
                  qt.name AS quest_type, d.name AS difficulty, l.name AS location,
                  u.id AS creator_id, u.username AS creator_username, u.name AS creator_name,
                  u.surname AS creator_surname, u.avatar_filename AS creator_avatar
           FROM quest_sessions qs
           JOIN quests q ON q.id = qs.quest_id
           JOIN quest_types qt ON qt.id = q.quest_type_id
           JOIN difficulties d ON d.id = q.difficulty_id
           JOIN locations l ON l.id = qs.location_id
           JOIN users u ON u.id = q.guild_master_id
           WHERE qs.id = ?""",
        (session_id,),
    ).fetchone()
    conn.close()
    return row


def get_sessions_for_quest(quest_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT qs.*, l.name AS location
           FROM quest_sessions qs
           JOIN locations l ON l.id = qs.location_id
           WHERE qs.quest_id = ?""",
        (quest_id,),
    ).fetchall()
    conn.close()
    return sorted(rows, key=lambda r: (DAY_ORDER.index(r["day"]), r["start_time"]))


def session_has_participants(session_id):
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM participations WHERE quest_session_id = ?", (session_id,)
    ).fetchone()[0]
    conn.close()
    return count > 0


def location_time_conflict_exists(day, start_time, end_time, location_id, exclude_session_id=None):
    """I check whether another session overlaps at the same place and day."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT qs.id, qs.start_time, q.duration_minutes
           FROM quest_sessions qs
           JOIN quests q ON q.id = qs.quest_id
           WHERE qs.day = ? AND qs.location_id = ?""",
        (day, location_id),
    ).fetchall()
    conn.close()

    def to_minutes(hhmm):
        h, m = map(int, hhmm.split(":"))
        return h * 60 + m

    new_start = to_minutes(start_time)
    new_end = to_minutes(end_time)

    for r in rows:
        if exclude_session_id and r["id"] == exclude_session_id:
            continue
        existing_start = to_minutes(r["start_time"])
        existing_end = existing_start + r["duration_minutes"]
        if new_start < existing_end and existing_start < new_end:
            return True
    return False


def create_session(quest_id, day, start_time, location_id):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO quest_sessions (quest_id, day, start_time, location_id) VALUES (?, ?, ?, ?)",
        (quest_id, day, start_time, location_id),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_session(session_id, day, start_time, location_id):
    conn = get_connection()
    conn.execute(
        "UPDATE quest_sessions SET day = ?, start_time = ?, location_id = ? WHERE id = ?",
        (day, start_time, location_id, session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id):
    conn = get_connection()
    conn.execute("DELETE FROM quest_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def get_role_reserved_counts(session_id):
    """I count the reserved places for each role in a session."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.name AS role_name, COALESCE(SUM(used.place_count), 0) AS reserved
           FROM roles r
           LEFT JOIN (
             SELECT role_id, COUNT(*) AS place_count
             FROM (
               SELECT role_id FROM participations WHERE quest_session_id = ?
               UNION ALL
               SELECT companion_role_id FROM participations
               WHERE quest_session_id = ? AND companion_role_id IS NOT NULL
             ) occupied
             GROUP BY role_id
           ) used ON used.role_id = r.id
           GROUP BY r.id""",
        (session_id, session_id),
    ).fetchall()
    conn.close()
    return {r["role_name"]: r["reserved"] for r in rows}


def get_role_availability(session_id):
    """I calculate how many places remain for each role."""
    roles = get_roles_for_session(session_id)
    reserved = get_role_reserved_counts(session_id)
    return {r["name"]: r["max_places_per_session"] - reserved.get(r["name"], 0) for r in roles}


def get_participation(session_id, adventurer_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT p.*, r.name AS role_name, cr.name AS companion_role_name
           FROM participations p
           JOIN roles r ON r.id = p.role_id
           LEFT JOIN roles cr ON cr.id = p.companion_role_id
           WHERE p.quest_session_id = ? AND p.adventurer_id = ?""",
        (session_id, adventurer_id),
    ).fetchone()
    conn.close()
    return row


def get_participations_for_adventurer(adventurer_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*, qs.day, qs.start_time, qs.quest_id, q.title, q.duration_minutes,
                  l.name AS location, r.name AS role_name, cr.name AS companion_role_name
           FROM participations p
           JOIN quest_sessions qs ON qs.id = p.quest_session_id
           JOIN quests q ON q.id = qs.quest_id
           JOIN locations l ON l.id = qs.location_id
           JOIN roles r ON r.id = p.role_id
           LEFT JOIN roles cr ON cr.id = p.companion_role_id
           WHERE p.adventurer_id = ?""",
        (adventurer_id,),
    ).fetchall()
    conn.close()
    return sorted(rows, key=lambda r: (DAY_ORDER.index(r["day"]), r["start_time"]))


def count_adventurer_sessions_this_week(adventurer_id):
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM participations WHERE adventurer_id = ?", (adventurer_id,)
    ).fetchone()[0]
    conn.close()
    return count


def create_participation(session_id, adventurer_id, role_id, places_reserved,
                         companion_name=None, companion_surname=None, companion_birthdate=None,
                         companion_email=None, companion_role_id=None):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO participations
           (quest_session_id, adventurer_id, role_id, places_reserved, companion_name,
            companion_surname, companion_birthdate, companion_email, companion_role_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, adventurer_id, role_id, places_reserved, companion_name, companion_surname,
         companion_birthdate, companion_email, companion_role_id),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_participation(participation_id, role_id, places_reserved,
                         companion_name=None, companion_surname=None, companion_birthdate=None,
                         companion_email=None, companion_role_id=None):
    conn = get_connection()
    conn.execute(
        """UPDATE participations
           SET role_id = ?, places_reserved = ?, companion_name = ?, companion_surname = ?,
               companion_birthdate = ?, companion_email = ?, companion_role_id = ?
           WHERE id = ?""",
        (role_id, places_reserved, companion_name, companion_surname, companion_birthdate,
         companion_email, companion_role_id, participation_id),
    )
    conn.commit()
    conn.close()


def delete_participation(participation_id):
    conn = get_connection()
    conn.execute("DELETE FROM participations WHERE id = ?", (participation_id,))
    conn.commit()
    conn.close()


def get_participation_by_id(participation_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM participations WHERE id = ?", (participation_id,)).fetchone()
    conn.close()
    return row


def get_other_sessions_for_adventurer(adventurer_id, exclude_session_id=None):
    """I get an adventurer's sessions so I can check time overlaps."""
    conn = get_connection()
    query = """
        SELECT qs.id, qs.day, qs.start_time, q.duration_minutes
        FROM participations p
        JOIN quest_sessions qs ON qs.id = p.quest_session_id
        JOIN quests q ON q.id = qs.quest_id
        WHERE p.adventurer_id = ?
    """
    params = [adventurer_id]
    if exclude_session_id:
        query += " AND qs.id != ?"
        params.append(exclude_session_id)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_session_stats(session_id):
    """I calculate the participation statistics for one session."""
    roles = get_roles_for_session(session_id)
    reserved = get_role_reserved_counts(session_id)

    per_role = []
    for r in roles:
        res = reserved.get(r["name"], 0)
        per_role.append({
            "role": r["name"],
            "reserved": res,
            "capacity": r["max_places_per_session"],
            "remaining": r["max_places_per_session"] - res,
        })

    total_reserved = sum(p["reserved"] for p in per_role)
    max_reserved = max((p["reserved"] for p in per_role), default=0)
    most_requested = [p["role"] for p in per_role if p["reserved"] == max_reserved and max_reserved > 0]

    total_capacity = sum(p["capacity"] for p in per_role)
    return {
        "per_role": per_role,
        "total_reserved": total_reserved,
        "total_capacity": total_capacity,
        "most_requested": most_requested,
    }


def get_quests_with_sessions_for_guildmaster(guild_master_id):
    """I get the Guild Master's quests and sessions for the dashboard."""
    conn = get_connection()
    quests = conn.execute(
        """SELECT q.*, qt.name AS quest_type, d.name AS difficulty
           FROM quests q
           JOIN quest_types qt ON qt.id = q.quest_type_id
           JOIN difficulties d ON d.id = q.difficulty_id
           WHERE q.guild_master_id = ?
           ORDER BY q.title""",
        (guild_master_id,),
    ).fetchall()
    conn.close()

    result = []
    for q in quests:
        sessions = get_sessions_for_quest(q["id"])
        sessions_with_counts = []
        for s in sessions:
            has_participants = session_has_participants(s["id"])
            sessions_with_counts.append({"session": s, "has_participants": has_participants})
        result.append({"quest": q, "sessions": sessions_with_counts})
    return result


def get_location_by_id(location_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
    conn.close()
    return row


def get_role_by_id(role_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
    conn.close()
    return row


def get_role_by_name(name):
    conn = get_connection()
    row = conn.execute("SELECT * FROM roles WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row



def get_comments_for_quest(quest_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, u.username, u.name, u.surname, u.avatar_filename,
                  strftime('%d/%m/%Y · %H:%M', c.created_at) AS created_label
           FROM quest_comments c
           JOIN users u ON u.id = c.user_id
           WHERE c.quest_id = ?
           ORDER BY c.created_at DESC""",
        (quest_id,),
    ).fetchall()
    conn.close()
    return rows


def create_comment(quest_id, user_id, comment_text):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO quest_comments (quest_id, user_id, comment_text) VALUES (?, ?, ?)",
        (quest_id, user_id, comment_text),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_comment_by_id(comment_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM quest_comments WHERE id = ?", (comment_id,)).fetchone()
    conn.close()
    return row


def delete_comment(comment_id):
    conn = get_connection()
    conn.execute("DELETE FROM quest_comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()


def get_participants_for_session(session_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*, u.username, u.name, u.surname, u.avatar_filename,
                  r.name AS role_name, cr.name AS companion_role_name
           FROM participations p
           JOIN users u ON u.id = p.adventurer_id
           JOIN roles r ON r.id = p.role_id
           LEFT JOIN roles cr ON cr.id = p.companion_role_id
           WHERE p.quest_session_id = ?
           ORDER BY r.id, u.username""",
        (session_id,),
    ).fetchall()
    conn.close()
    return rows
