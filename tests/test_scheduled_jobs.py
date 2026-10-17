from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services import scheduled_jobs


def test_progress_job_uses_current_week():
    local_today = date(2026, 10, 14)  # Wednesday
    now = datetime(2026, 10, 14, 3, 30, tzinfo=timezone.utc)

    with (
        patch.object(
            scheduled_jobs,
            "_get_local_date_and_now",
            return_value=(local_today, now),
        ),
        patch.object(
            scheduled_jobs,
            "_process_week_for_active_employees",
        ) as mock_process,
    ):
        scheduled_jobs.run_progress_notification_check()

    mock_process.assert_called_once_with(
        week_start=date(2026, 10, 12),  # Monday
        as_of_date=local_today,
        now=now,
    )


def test_final_job_uses_previous_week_after_grace_period():
    local_today = date(2026, 10, 20)  # Tuesday
    now = datetime(2026, 10, 19, 0, 35, tzinfo=timezone.utc)

    with (
        patch.object(
            scheduled_jobs,
            "_get_local_date_and_now",
            return_value=(local_today, now),
        ),
        patch.object(
            scheduled_jobs,
            "is_final_evaluation_due",
            return_value=True,
        ) as mock_due,
        patch.object(
            scheduled_jobs,
            "_process_week_for_active_employees",
        ) as mock_process,
    ):
        scheduled_jobs.run_final_weekly_notification_check()

    mock_due.assert_called_once_with(
        week_start=date(2026, 10, 12),
        now=now,
    )
    mock_process.assert_called_once_with(
        week_start=date(2026, 10, 12),
        as_of_date=date(2026, 10, 18),  # Sunday
        now=now,
    )


def test_final_job_skips_processing_before_grace_period():
    local_today = date(2026, 10, 19)  # Monday
    now = datetime(2026, 10, 18, 18, 0, tzinfo=timezone.utc)

    with (
        patch.object(
            scheduled_jobs,
            "_get_local_date_and_now",
            return_value=(local_today, now),
        ),
        patch.object(
            scheduled_jobs,
            "is_final_evaluation_due",
            return_value=False,
        ),
        patch.object(
            scheduled_jobs,
            "_process_week_for_active_employees",
        ) as mock_process,
    ):
        scheduled_jobs.run_final_weekly_notification_check()

    mock_process.assert_not_called()


def test_employee_failure_does_not_stop_next_employee():
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [1, 2]

    session_context = MagicMock()
    session_context.__enter__.return_value = mock_db

    first_result = RuntimeError("Simulated employee failure")

    with (
        patch.object(
            scheduled_jobs,
            "SessionLocal",
            return_value=session_context,
        ),
        patch.object(
            scheduled_jobs,
            "process_employee_week",
            side_effect=[first_result, {"notifications": []}],
        ) as mock_process,
    ):
        scheduled_jobs._process_week_for_active_employees(
            week_start=date(2026, 10, 12),
            as_of_date=date(2026, 10, 14),
            now=datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc),
        )

    assert mock_process.call_count == 2
    mock_db.rollback.assert_called_once()
    session_context.__exit__.assert_called_once()


def test_invalid_week_start_is_rejected_before_opening_database():
    with patch.object(scheduled_jobs, "SessionLocal") as mock_session:
        with pytest.raises(ValueError, match="week_start must be a Monday"):
            scheduled_jobs._process_week_for_active_employees(
                week_start=date(2026, 10, 13),  # Tuesday
                as_of_date=date(2026, 10, 14),
                now=datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc),
            )

    mock_session.assert_not_called()

def test_progress_job_processes_attendance_before_email_delivery():
    local_today = date(2026, 10, 14)  # Wednesday
    now = datetime(2026, 10, 14, 3, 30, tzinfo=timezone.utc)
    call_order = []

    def record_processing(**kwargs):
        call_order.append("process")

    def record_delivery():
        call_order.append("deliver")

    with (
        patch.object(
            scheduled_jobs,
            "_get_local_date_and_now",
            return_value=(local_today, now),
        ),
        patch.object(
            scheduled_jobs,
            "_process_week_for_active_employees",
            side_effect=record_processing,
        ),
        patch.object(
            scheduled_jobs,
            "_deliver_pending_emails",
            side_effect=record_delivery,
        ),
    ):
        scheduled_jobs.run_progress_notification_check()

    assert call_order == ["process", "deliver"]

def test_final_job_delivers_emails_after_processing_previous_week():
    local_today = date(2026, 10, 20)  # Tuesday
    now = datetime(2026, 10, 19, 0, 35, tzinfo=timezone.utc)
    call_order = []

    def record_processing(**kwargs):
        call_order.append("process")

    def record_delivery():
        call_order.append("deliver")

    with (
        patch.object(
            scheduled_jobs,
            "_get_local_date_and_now",
            return_value=(local_today, now),
        ),
        patch.object(
            scheduled_jobs,
            "is_final_evaluation_due",
            return_value=True,
        ),
        patch.object(
            scheduled_jobs,
            "_process_week_for_active_employees",
            side_effect=record_processing,
        ),
        patch.object(
            scheduled_jobs,
            "_deliver_pending_emails",
            side_effect=record_delivery,
        ),
    ):
        scheduled_jobs.run_final_weekly_notification_check()

    assert call_order == ["process", "deliver"]