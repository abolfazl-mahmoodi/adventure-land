"""I keep the fictional week and time calculations in this file."""

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MODIFY_CUTOFF_MINUTES = 8 * 60  # I lock participation changes 8 hours before a session.


def to_absolute_minutes(day, hhmm):
    """I convert a fictional day and time into minutes from Monday."""
    day_index = DAY_ORDER.index(day)
    hours, minutes = map(int, hhmm.split(":"))
    return day_index * 24 * 60 + hours * 60 + minutes


def minutes_until(session_day, session_time, now_day, now_time):
    """I calculate how many minutes remain until a session."""
    return to_absolute_minutes(session_day, session_time) - to_absolute_minutes(now_day, now_time)


def is_participation_modifiable(session_day, session_time, now_day, now_time):
    """I allow changes only when the session starts more than 8 hours later."""
    return minutes_until(session_day, session_time, now_day, now_time) > MODIFY_CUTOFF_MINUTES


def format_time_until(session_day, session_time, now_day, now_time):
    """I make the time difference easy to read on the page."""
    delta = minutes_until(session_day, session_time, now_day, now_time)
    past = delta < 0
    delta = abs(delta)
    days, rem = divmod(delta, 24 * 60)
    hours, minutes = divmod(rem, 60)

    if days > 0:
        text = f"{days}d {hours}h"
    elif hours > 0:
        text = f"{hours}h {minutes}m"
    else:
        text = f"{minutes}m"

    return f"Started {text} ago" if past else f"Starts in {text}"
