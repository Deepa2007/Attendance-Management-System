from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from app.models.attendance_notification import AttendanceNotification
from app.services.notifications import create_notification


def test_create_notification_adds_pending_notification():
    db = MagicMock()
    db.scalar.return_value = None

    scheduled_at = datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc)

    result = create_notification(
        db,
        employee_id=1,
        week_start=date(2026, 10, 12),
        notification_type="progress_reminder",
        milestone_key="wednesday",
        recipient_email="employee@example.com",
        scheduled_at=scheduled_at,
        tenant_id=1,
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(result)

    assert isinstance(result, AttendanceNotification)
    assert result.employee_id == 1
    assert result.week_start == date(2026, 10, 12)
    assert result.notification_type == "progress_reminder"
    assert result.milestone_key == "wednesday"
    assert result.recipient_email == "employee@example.com"
    assert result.status == "pending"
    assert result.attempt_count == 0
    assert result.scheduled_at == scheduled_at


def test_duplicate_notification_returns_existing_record():
    existing = AttendanceNotification(
        id=10,
        tenant_id=1,
        employee_id=1,
        week_start=date(2026, 10, 12),
        notification_type="progress_reminder",
        milestone_key="wednesday",
        recipient_email="employee@example.com",
        status="pending",
        scheduled_at=datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc),
        attempt_count=0,
    )

    db = MagicMock()
    db.scalar.return_value = existing

    result = create_notification(
        db,
        employee_id=1,
        week_start=date(2026, 10, 12),
        notification_type="progress_reminder",
        milestone_key="wednesday",
        recipient_email="employee@example.com",
        scheduled_at=datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc),
        tenant_id=1,
    )

    assert result is existing
    db.add.assert_not_called()
    db.commit.assert_not_called()
