from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attendance_notification import AttendanceNotification


def create_notification(
    db: Session,
    *,
    employee_id: int,
    week_start: date,
    notification_type: str,
    milestone_key: str,
    recipient_email: str,
    scheduled_at: datetime,
    tenant_id: int,
) -> AttendanceNotification:
    """
    Create a notification if one with the same deduplication key
    does not already exist.

    The database uniqueness constraint is the final protection
    against concurrent duplicate creation.
    """
    existing = db.scalar(
        select(AttendanceNotification).where(
            AttendanceNotification.employee_id == employee_id,
            AttendanceNotification.week_start == week_start,
            AttendanceNotification.notification_type == notification_type,
            AttendanceNotification.milestone_key == milestone_key,
        )
    )

    if existing is not None:
        return existing

    notification = AttendanceNotification(
        tenant_id=tenant_id,
        employee_id=employee_id,
        week_start=week_start,
        notification_type=notification_type,
        milestone_key=milestone_key,
        recipient_email=recipient_email,
        status="pending",
        scheduled_at=scheduled_at,
        attempt_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(notification)

    try:
        db.commit()
    except IntegrityError:
        # Another worker may have created the same notification
        # after our initial lookup.
        db.rollback()

        existing = db.scalar(
            select(AttendanceNotification).where(
                AttendanceNotification.employee_id == employee_id,
                AttendanceNotification.week_start == week_start,
                AttendanceNotification.notification_type == notification_type,
                AttendanceNotification.milestone_key == milestone_key,
            )
        )

        if existing is not None:
            return existing

        raise

    db.refresh(notification)
    return notification
