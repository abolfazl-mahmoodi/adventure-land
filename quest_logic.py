"""I keep the participation rules separate so they are easier to check."""

import dao
import week_time

MAX_SESSIONS_PER_WEEK = 3
MAX_PLACES_PER_JOIN = 2


def _to_minutes(day, hhmm):
    return week_time.to_absolute_minutes(day, hhmm)


def _overlaps(day_a, start_a, duration_a, day_b, start_b, duration_b):
    start_a_min = _to_minutes(day_a, start_a)
    end_a_min = start_a_min + duration_a
    start_b_min = _to_minutes(day_b, start_b)
    end_b_min = start_b_min + duration_b
    return start_a_min < end_b_min and start_b_min < end_a_min


def session_is_in_the_past(session_day, session_start_time):
    now_day, now_time = dao.get_simulated_now()["current_day"], dao.get_simulated_now()["current_time_hhmm"]
    return week_time.to_absolute_minutes(session_day, session_start_time) <= week_time.to_absolute_minutes(now_day, now_time)


def _requested_role_counts(role_name, places_reserved, companion_role_name=None):
    requested = {role_name: 1}
    if places_reserved == 2:
        requested[companion_role_name] = requested.get(companion_role_name, 0) + 1
    return requested


def can_join_session(session_id, adventurer_id, role_name, places_reserved, companion_role_name=None):
    """I check every rule before an adventurer joins a session."""
    session = dao.get_session_by_id(session_id)
    if session is None:
        return False, "This quest session no longer exists."

    now_row = dao.get_simulated_now()
    if week_time.to_absolute_minutes(session["day"], session["start_time"]) <= \
            week_time.to_absolute_minutes(now_row["current_day"], now_row["current_time_hhmm"]):
        return False, "This quest session has already taken place and can no longer be joined."

    if dao.get_participation(session_id, adventurer_id) is not None:
        return False, "You have already joined this quest session. Edit your existing participation instead."

    if places_reserved not in (1, 2):
        return False, "You can reserve either 1 or 2 places (2 if bringing a companion)."

    if dao.get_role_by_name(role_name) is None:
        return False, "Please select a valid role."
    if places_reserved == 2 and dao.get_role_by_name(companion_role_name) is None:
        return False, "Please select a valid role for your companion."

    availability = dao.get_role_availability(session_id)
    for requested_role, amount in _requested_role_counts(role_name, places_reserved, companion_role_name).items():
        if requested_role not in availability:
            return False, f"{requested_role} is not available for this quest type."
        if availability.get(requested_role, 0) < amount:
            return False, f"Not enough {requested_role} places left in this session."

    current_count = dao.count_adventurer_sessions_this_week(adventurer_id)
    if current_count >= MAX_SESSIONS_PER_WEEK:
        return False, f"You've already joined the maximum of {MAX_SESSIONS_PER_WEEK} quest sessions this week."

    other_sessions = dao.get_other_sessions_for_adventurer(adventurer_id)
    for other in other_sessions:
        if _overlaps(session["day"], session["start_time"], session["duration_minutes"],
                     other["day"], other["start_time"], other["duration_minutes"]):
            return False, "This quest session overlaps in time with another quest session you've already joined."

    return True, None


def can_modify_participation(participation_id, adventurer_id, new_role_name, new_places_reserved,
                             companion_role_name=None):
    """I check whether an existing participation can be changed."""
    participation = dao.get_participation_by_id(participation_id)
    if participation is None or participation["adventurer_id"] != adventurer_id:
        return False, "Participation not found."

    session = dao.get_session_by_id(participation["quest_session_id"])
    now_row = dao.get_simulated_now()
    if not week_time.is_participation_modifiable(
        session["day"], session["start_time"], now_row["current_day"], now_row["current_time_hhmm"]
    ):
        return False, "This participation can no longer be modified — the quest session starts within 8 hours."

    if new_places_reserved not in (1, 2):
        return False, "You can reserve either 1 or 2 places (2 if bringing a companion)."

    if dao.get_role_by_name(new_role_name) is None:
        return False, "Please select a valid role."
    if new_places_reserved == 2 and dao.get_role_by_name(companion_role_name) is None:
        return False, "Please select a valid role for your companion."

    # I add the current places back before checking the new role choices.
    availability = dao.get_role_availability(session["id"])
    current_role = dao.get_role_by_id(participation["role_id"])["name"]
    availability[current_role] = availability.get(current_role, 0) + 1
    if participation["companion_role_id"]:
        current_companion_role = dao.get_role_by_id(participation["companion_role_id"])["name"]
        availability[current_companion_role] = availability.get(current_companion_role, 0) + 1

    for requested_role, amount in _requested_role_counts(
        new_role_name, new_places_reserved, companion_role_name
    ).items():
        if requested_role not in availability:
            return False, f"{requested_role} is not available for this quest type."
        if availability.get(requested_role, 0) < amount:
            return False, f"Not enough {requested_role} places left in this session."

    return True, None


def can_cancel_participation(participation_id, adventurer_id):
    participation = dao.get_participation_by_id(participation_id)
    if participation is None or participation["adventurer_id"] != adventurer_id:
        return False, "Participation not found."

    session = dao.get_session_by_id(participation["quest_session_id"])
    now_row = dao.get_simulated_now()
    if not week_time.is_participation_modifiable(
        session["day"], session["start_time"], now_row["current_day"], now_row["current_time_hhmm"]
    ):
        return False, "This participation can no longer be cancelled — the quest session starts within 8 hours."

    return True, None
