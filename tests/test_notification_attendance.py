
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.notification_attendance import (
    get_completed_seconds_by_day,
)


def make_session(start, end):
    return SimpleNamespace(
        checked_in_at=start,
        checked_out_at=end,
    )


def run_helper(sessions, *, week_start, as_of_date):
    db = MagicMock()
    db.scalars.return_value.all.return_value = sessions

    result = get_completed_seconds_by_day(
        db,
        employee_id=1,
        week_start=week_start,
        as_of_date=as_of_date,
    )
    return result


def test_completed_session_is_counted_on_local_day():
    # 09:00–14:00 IST = 03:30–08:30 UTC.
    session = make_session(
        datetime(2026, 10, 12, 3, 30, tzinfo=timezone.utc),
        datetime(2026, 10, 12, 8, 30, tzinfo=timezone.utc),
    )

    result = run_helper(
        [session],
        week_start=date(2026, 10, 12),
        as_of_date=date(2026, 10, 12),
    )

    assert result == {date(2026, 10, 12): 5 * 3600}


def test_overnight_session_is_split_at_local_midnight():
    # 23:00 IST Monday to 02:00 IST Tuesday.
    session = make_session(
        datetime(2026, 10, 12, 17, 30, tzinfo=timezone.utc),
        datetime(2026, 10, 12, 20, 30, tzinfo=timezone.utc),
    )

    result = run_helper(
        [session],
        week_start=date(2026, 10, 12),
        as_of_date=date(2026, 10, 13),
    )

    assert result == {
        date(2026, 10, 12): 3600,
        date(2026, 10, 13): 2 * 3600,
    }


def test_rejects_week_start_that_is_not_monday():
    db = MagicMock()

    with pytest.raises(ValueError, match="week_start must be a Monday"):
        get_completed_seconds_by_day(
            db,
            employee_id=1,
            week_start=date(2026, 10, 13),
            as_of_date=date(2026, 10, 13),
        )


def test_rejects_as_of_date_before_week_start():
    db = MagicMock()

    with pytest.raises(ValueError, match="as_of_date cannot be before"):
        get_completed_seconds_by_day(
            db,
            employee_id=1,
            week_start=date(2026, 10, 12),
            as_of_date=date(2026, 10, 11),
        )
