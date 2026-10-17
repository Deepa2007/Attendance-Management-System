from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.attendance_notification import AttendanceNotification
from app.services.email_provider import FakeEmailProvider
from app.services.notification_delivery import deliver_pending_notifications


NOW = datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc)


def make_notification():
    return AttendanceNotification(
        id=10,
        employee_id=1,
        week_start=date(2026, 10, 12),
        notification_type="progress_reminder",
        milestone_key="progress_2026-10-14",
        recipient_email="employee@example.com",
        status="pending",
        scheduled_at=datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc),
        attempt_count=0,
    )


def test_successful_delivery_marks_notification_sent():
    notification = make_notification()
    db = MagicMock()
    db.scalar.return_value = notification
    provider = FakeEmailProvider()

    with patch(
        "app.services.notification_delivery.build_notification_email"
    ) as mock_builder:
        from app.services.email_provider import EmailMessage

        mock_builder.return_value = EmailMessage(
            recipient="employee@example.com",
            subject="Attendance reminder",
            body="Please review your attendance.",
        )

        # First query claims the notification; second query finds no more work.
        db.scalar.side_effect = [notification, None]

        result = deliver_pending_notifications(
            db,
            provider=provider,
            now=NOW,
            batch_size=5,
        )

    assert result == {"claimed": 1, "sent": 1, "failed": 0}
    assert notification.status == "sent"
    assert notification.attempt_count == 1
    assert notification.sent_at is not None
    assert len(provider.sent_messages) == 1


def test_provider_failure_marks_notification_failed():
    notification = make_notification()
    db = MagicMock()
    db.scalar.side_effect = [notification, None]

    provider = MagicMock()
    provider.send.side_effect = RuntimeError("Simulated email failure")

    with patch(
        "app.services.notification_delivery.build_notification_email"
    ) as mock_builder:
        from app.services.email_provider import EmailMessage

        mock_builder.return_value = EmailMessage(
            recipient="employee@example.com",
            subject="Attendance reminder",
            body="Please review your attendance.",
        )

        # The notification is still returned by db.get after rollback.
        db.get.return_value = notification

        result = deliver_pending_notifications(
            db,
            provider=provider,
            now=NOW,
            batch_size=5,
        )

    assert result == {"claimed": 1, "sent": 0, "failed": 1}
    assert notification.status == "failed"
    assert notification.attempt_count == 1
    assert "Simulated email failure" in notification.last_error


def test_naive_datetime_is_rejected():
    db = MagicMock()
    provider = FakeEmailProvider()

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        deliver_pending_notifications(
            db,
            provider=provider,
            now=datetime(2026, 10, 16, 9, 0),
        )

    db.scalar.assert_not_called()


def test_invalid_batch_size_is_rejected():
    db = MagicMock()
    provider = FakeEmailProvider()

    with pytest.raises(ValueError, match="batch_size must be at least 1"):
        deliver_pending_notifications(
            db,
            provider=provider,
            now=NOW,
            batch_size=0,
        )

    db.scalar.assert_not_called()

def test_stale_sending_notification_can_be_reclaimed():
    notification = make_notification()
    notification.status = "sending"
    notification.attempt_count = 1
    notification.updated_at = datetime(
        2026, 10, 16, 8, 30, tzinfo=timezone.utc
    )

    db = MagicMock()
    db.scalar.side_effect = [notification, None]

    provider = FakeEmailProvider()

    with patch(
        "app.services.notification_delivery.build_notification_email"
    ) as mock_builder:
        from app.services.email_provider import EmailMessage

        mock_builder.return_value = EmailMessage(
            recipient="employee@example.com",
            subject="Attendance reminder",
            body="Please review your attendance.",
        )

        result = deliver_pending_notifications(
            db,
            provider=provider,
            now=NOW,
            batch_size=1,
        )

    assert result == {"claimed": 1, "sent": 1, "failed": 0}
    assert notification.status == "sent"
    assert notification.attempt_count == 2


def test_notification_at_attempt_limit_is_not_reclaimed():
    db = MagicMock()
    db.scalar.return_value = None
    provider = FakeEmailProvider()

    result = deliver_pending_notifications(
        db,
        provider=provider,
        now=NOW,
        batch_size=5,
    )

    assert result == {"claimed": 0, "sent": 0, "failed": 0}
    assert provider.sent_messages == []
