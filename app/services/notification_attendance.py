
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attendance import AttendanceSession


def get_completed_seconds_by_day(
    db: Session,
    *,
    employee_id: int,
    week_start: date,
    as_of_date: date,
) -> dict[date, int]:
    """
    Return completed attendance seconds by local calendar day.

    Only completed sessions are included. Overnight sessions are
    split at local midnight, and future dates are excluded.
    """

    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    week_end = week_start + timedelta(days=6)

    if as_of_date < week_start:
        raise ValueError("as_of_date cannot be before week_start")

    effective_end = min(as_of_date, week_end)

    company_tz = ZoneInfo(settings.company_timezone)

    local_start = datetime.combine(
        week_start,
        time.min,
        tzinfo=company_tz,
    )
    local_end_exclusive = datetime.combine(
        effective_end + timedelta(days=1),
        time.min,
        tzinfo=company_tz,
    )

    utc_start = local_start.astimezone(timezone.utc)
    utc_end_exclusive = local_end_exclusive.astimezone(timezone.utc)

    sessions = db.scalars(
        select(AttendanceSession)
        .where(
            AttendanceSession.employee_id == employee_id,
            AttendanceSession.checked_out_at.is_not(None),
            AttendanceSession.checked_in_at < utc_end_exclusive,
            AttendanceSession.checked_out_at > utc_start,
        )
        .order_by(AttendanceSession.checked_in_at)
    ).all()

    seconds_by_day: dict[date, int] = {}

    for session in sessions:
        if session.checked_out_at is None:
            continue

        cursor = max(session.checked_in_at, utc_start)
        session_end = min(
            session.checked_out_at,
            utc_end_exclusive,
        )

        while cursor < session_end:
            local_cursor = cursor.astimezone(company_tz)

            next_midnight = datetime.combine(
                local_cursor.date() + timedelta(days=1),
                time.min,
                tzinfo=company_tz,
            )
            next_midnight_utc = next_midnight.astimezone(timezone.utc)

            segment_end = min(session_end, next_midnight_utc)
            seconds = int((segment_end - cursor).total_seconds())

            current_day = local_cursor.date()
            seconds_by_day[current_day] = (
                seconds_by_day.get(current_day, 0) + seconds
            )

            cursor = segment_end

    return seconds_by_day
