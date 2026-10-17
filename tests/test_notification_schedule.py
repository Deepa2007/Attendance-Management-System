
from datetime import date, datetime, timezone

import pytest

from app.services.notification_schedule import (
    get_final_evaluation_time,
    get_week_end,
    is_final_evaluation_due,
)


WEEK_START = date(2026, 10, 12)


def test_week_end_is_sunday():
    assert get_week_end(WEEK_START) == date(2026, 10, 18)


def test_week_start_must_be_monday():
    with pytest.raises(ValueError, match="Monday"):
        get_week_end(date(2026, 10, 13))


def test_final_evaluation_includes_24_hour_grace_period():
    due_at = get_final_evaluation_time(WEEK_START)

    # Monday 00:00 IST plus 24 hours = Tuesday 00:00 IST.
    assert due_at == datetime(2026, 10, 19, 18, 30, tzinfo=timezone.utc)


def test_final_evaluation_not_due_before_deadline():
    due_at = get_final_evaluation_time(WEEK_START)

    assert is_final_evaluation_due(
        week_start=WEEK_START,
        now=due_at.replace(minute=29, second=59),
    ) is False


def test_final_evaluation_due_at_deadline():
    due_at = get_final_evaluation_time(WEEK_START)

    assert is_final_evaluation_due(
        week_start=WEEK_START,
        now=due_at,
    ) is True


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        is_final_evaluation_due(
            week_start=WEEK_START,
            now=datetime(2026, 10, 20, 0, 0),
        )
