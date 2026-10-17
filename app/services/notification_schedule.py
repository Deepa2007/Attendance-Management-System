from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings


FINAL_GRACE_PERIOD = timedelta(hours=24)


def get_week_end(week_start: date) -> date:
    """Return the Sunday belonging to a Monday-starting week."""
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    return week_start + timedelta(days=6)


def get_final_evaluation_time(week_start: date) -> datetime:
    """
    Return the instant when the weekly 24-hour grace period ends.

    The returned datetime is timezone-aware and expressed in UTC.
    """
    week_end = get_week_end(week_start)
    company_tz = ZoneInfo(settings.company_timezone)

    next_monday_local = datetime.combine(
        week_end + timedelta(days=1),
        time.min,
        tzinfo=company_tz,
    )

    grace_period_end_local = next_monday_local + FINAL_GRACE_PERIOD

    return grace_period_end_local.astimezone(ZoneInfo("UTC"))


def is_final_evaluation_due(
    *,
    week_start: date,
    now: datetime,
) -> bool:
    """
    Return True when the weekly grace period has ended.

    `now` must be timezone-aware.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    due_at = get_final_evaluation_time(week_start)

    return now.astimezone(ZoneInfo("UTC")) >= due_at
