from datetime import datetime, timezone, timedelta
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attendance_notification import AttendanceNotification
from app.services.email_provider import FakeEmailProvider
from app.services.notification_messages import build_notification_email


logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BATCH_SIZE = 50
STALE_SENDING_TIMEOUT = timedelta(minutes=10)

def deliver_pending_notifications(
    db: Session,
    *,
    provider: FakeEmailProvider,
    now: datetime | None = None,
    batch_size: int = BATCH_SIZE,
) -> dict[str, int]:
    """
    Claim and deliver a batch of pending or retryable notifications.

    The notification is marked as sending and committed before calling
    the provider. This reduces duplicate claims across concurrent workers.
    """

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    sent_count = 0
    failed_count = 0
    claimed_count = 0

    for _ in range(batch_size):
        try:
            stale_before = now - STALE_SENDING_TIMEOUT
            notification = db.scalar(
                select(AttendanceNotification)
               .where(
                    AttendanceNotification.attempt_count < MAX_ATTEMPTS,
                    AttendanceNotification.scheduled_at <= now,
                   (
                        AttendanceNotification.status.in_(["pending", "failed"])
                        | (
                            (AttendanceNotification.status == "sending")
                            & (AttendanceNotification.updated_at <= stale_before)
                        )
                       ),
                )
                .order_by(
                    AttendanceNotification.scheduled_at,
                    AttendanceNotification.id,
                )
                .with_for_update(skip_locked=True)
                .limit(1)
            )

            if notification is None:
                db.commit()
                break

            notification.status = "sending"
            notification.attempt_count += 1
            notification.updated_at = now
            notification.last_error = None
            db.commit()
            claimed_count += 1

        except Exception:
            db.rollback()
            logger.exception("Could not claim a pending notification")
            break

        try:
            message = build_notification_email(
                recipient_email=notification.recipient_email,
                notification_type=notification.notification_type,
                week_start=notification.week_start,
                milestone_key=notification.milestone_key,
            )

            provider.send(message)

            notification.status = "sent"
            notification.sent_at = datetime.now(timezone.utc)
            notification.updated_at = datetime.now(timezone.utc)
            notification.last_error = None
            db.commit()
            sent_count += 1

        except Exception as exc:
            db.rollback()
            failed_count += 1

            try:
                failed_notification = db.get(
                    AttendanceNotification,
                    notification.id,
                    with_for_update=True,
                )

                if failed_notification is not None:
                    failed_notification.status = "failed"
                    failed_notification.last_error = str(exc)[:4000]
                    failed_notification.updated_at = datetime.now(timezone.utc)
                    db.commit()

            except Exception:
                db.rollback()
                logger.exception(
                    "Could not record failure for notification_id=%s",
                    notification.id,
                )

            logger.exception(
                "Notification delivery failed: notification_id=%s",
                notification.id,
            )

    return {
        "claimed": claimed_count,
        "sent": sent_count,
        "failed": failed_count,
    }
