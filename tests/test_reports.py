
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.services.reports import get_employee_attendance_report


TZ = ZoneInfo(settings.company_timezone)


def local_time(day, hour, minute=0):
    """Create a timezone-aware timestamp in the company timezone."""
    return datetime(
        day.year, day.month, day.day, hour, minute, tzinfo=TZ
    ).astimezone(timezone.utc)


def make_session(start, end):
    """Create a temporary attendance-session object for testing."""
    return SimpleNamespace(
        checked_in_at=start,
        checked_out_at=end,
    )


def make_database(sessions):
    """Mock database results without changing PostgreSQL."""
    db = MagicMock()
    db.get.return_value = SimpleNamespace(
        id=1,
        full_name="Test Employee",
        email="report-test@example.com",
    )
    db.scalars.return_value.all.return_value = sessions
    return db


def test_exactly_five_hours_qualifies_for_daily_target():
    day = date(2026, 10, 12)  # Monday
    db = make_database([
        make_session(local_time(day, 9), local_time(day, 14))
    ])

    report = get_employee_attendance_report(
        db, 1, day, day
    )

    assert report.daily_records[0].total_seconds == 5 * 3600
    assert report.daily_records[0].meets_daily_target is True
    assert report.qualifying_days == 1


def test_less_than_five_hours_does_not_qualify():
    day = date(2026, 10, 12)
    db = make_database([
        make_session(
            local_time(day, 9),
            local_time(day, 13, 59),
        )
    ])

    report = get_employee_attendance_report(
        db, 1, day, day
    )

    assert report.daily_records[0].total_seconds == 4 * 3600 + 59 * 60
    assert report.daily_records[0].meets_daily_target is False
    assert report.qualifying_days == 0


def test_three_qualifying_days_and_fifteen_hours_is_compliant():
    monday = date(2026, 10, 12)
    sessions = [
        make_session(
            local_time(monday, 9),
            local_time(monday, 14),
        ),
        make_session(
            local_time(date(2026, 10, 13), 9),
            local_time(date(2026, 10, 13), 14),
        ),
        make_session(
            local_time(date(2026, 10, 14), 9),
            local_time(date(2026, 10, 14), 14),
        ),
    ]
    db = make_database(sessions)

    report = get_employee_attendance_report(
        db, 1, monday, date(2026, 10, 18)
    )

    assert report.complete_weeks_evaluated == 1
    assert report.weekly_records[0].qualifying_days == 3
    assert report.weekly_records[0].total_seconds == 15 * 3600
    assert report.weekly_records[0].is_compliant is True


def test_fifteen_hours_over_only_two_days_is_not_compliant():
    monday = date(2026, 10, 12)
    tuesday = date(2026, 10, 13)
    db = make_database([
        make_session(
            local_time(monday, 8),
            local_time(monday, 15, 30),
        ),
        make_session(
            local_time(tuesday, 8),
            local_time(tuesday, 15, 30),
        ),
    ])

    report = get_employee_attendance_report(
        db, 1, monday, date(2026, 10, 18)
    )

    week = report.weekly_records[0]
    assert week.total_seconds == 15 * 3600
    assert week.qualifying_days == 2
    assert week.meets_weekly_hours_requirement is True
    assert week.meets_daily_requirements is False
    assert week.is_compliant is False


def test_overnight_session_is_split_between_local_dates():
    day = date(2026, 10, 12)
    next_day = date(2026, 10, 13)
    db = make_database([
        make_session(
            local_time(day, 22),
            local_time(next_day, 2),
        )
    ])

    report = get_employee_attendance_report(
        db, 1, day, next_day
    )

    assert report.daily_records[0].total_seconds == 2 * 3600
    assert report.daily_records[1].total_seconds == 2 * 3600
    assert report.total_seconds == 4 * 3600


def test_incomplete_session_is_excluded():
    day = date(2026, 10, 12)
    db = make_database([
        make_session(local_time(day, 9), None)
    ])

    report = get_employee_attendance_report(
        db, 1, day, day
    )

    assert report.daily_records[0].total_seconds == 0
    assert report.qualifying_days == 0
