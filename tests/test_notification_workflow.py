
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.notification_workflow import process_employee_week


WEEK_START = date(2026, 10, 12)
AS_OF_DATE = date(2026, 10, 14)
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def make_employee():
    return SimpleNamespace(
        id=1,
        tenant_id=7,
        email="employee@example.com",
        is_active=True,
    )


def make_policy_status():
    return SimpleNamespace(
        week_start=WEEK_START,
        week_end=date(2026, 10, 18),
        qualifying_days=1,
        completed_seconds=6 * 3600,
        remaining_days=4,
        meets_daily_requirement=False,
        meets_weekly_hours_requirement=False,
        is_compliant=False,
        can_still_meet_daily_requirement=True,
        can_still_meet_weekly_hours_requirement=True,
        compliance_is_impossible=False,
        is_behind_schedule=True,
    )


@patch("app.services.notification_workflow.create_notification")
@patch("app.services.notification_workflow.decide_notifications")
@patch("app.services.notification_workflow.evaluate_weekly_policy")
@patch("app.services.notification_workflow.get_completed_seconds_by_day")
def test_workflow_creates_notifications_for_active_employee(
    mock_get_seconds,
    mock_evaluate,
    mock_decide,
    mock_create,
):
    db = MagicMock()
    db.scalar.return_value = make_employee()

    mock_get_seconds.return_value = {
        AS_OF_DATE: 6 * 3600,
    }
    mock_evaluate.return_value = make_policy_status()

    decision = SimpleNamespace(
        notification_type="progress_reminder",
        milestone_key="progress_2026-10-14",
    )
    mock_decide.return_value = [decision]

    saved_notification = SimpleNamespace(status="pending")
    mock_create.return_value = saved_notification

    result = process_employee_week(
        db,
        employee_id=1,
        week_start=WEEK_START,
        as_of_date=AS_OF_DATE,
        now=NOW,
    )

    assert result["employee_id"] == 1
    assert result["policy_status"] is mock_evaluate.return_value
    assert result["decisions"] == [decision]
    assert result["notifications"] == [saved_notification]

    mock_create.assert_called_once_with(
        db,
        employee_id=1,
        week_start=WEEK_START,
        notification_type="progress_reminder",
        milestone_key="progress_2026-10-14",
        recipient_email="employee@example.com",
        scheduled_at=NOW,
        tenant_id=7,
    )


def test_workflow_rejects_non_monday_week_start():
    db = MagicMock()

    with pytest.raises(ValueError, match="week_start must be a Monday"):
        process_employee_week(
            db,
            employee_id=1,
            week_start=date(2026, 10, 13),
            as_of_date=AS_OF_DATE,
            now=NOW,
        )

    db.scalar.assert_not_called()


def test_workflow_rejects_naive_datetime():
    db = MagicMock()
    db.scalar.return_value = make_employee()

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        process_employee_week(
            db,
            employee_id=1,
            week_start=WEEK_START,
            as_of_date=AS_OF_DATE,
            now=datetime(2026, 10, 14, 12, 0),
        )
