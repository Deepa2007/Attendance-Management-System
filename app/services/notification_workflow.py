
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.employee import Employee
from app.services.attendance_policy import evaluate_weekly_policy
from app.services.notification_attendance import (
    get_completed_seconds_by_day,
)
from app.services.notification_decisions import decide_notifications
from app.services.notification_schedule import is_final_evaluation_due
from app.services.notifications import create_notification


def process_employee_week(
    db: Session,
    *,
    employee_id: int,
    week_start: date,
    as_of_date: date,
    now: datetime | None = None,
):
    """
    Evaluate one employee's attendance week and create applicable
    pending notification records.

    This function does not send emails.
    """

    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    if as_of_date < week_start:
        raise ValueError("as_of_date cannot be before week_start")

    employee = db.scalar(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.is_active.is_(True),
        )
    )

    if employee is None:
        raise ValueError("Active employee was not found")

    company_tz = ZoneInfo(settings.company_timezone)

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    local_today = now.astimezone(company_tz).date()
    effective_as_of_date = min(as_of_date, local_today)

    if effective_as_of_date < week_start:
        raise ValueError("as_of_date cannot be before week_start")

    daily_seconds = get_completed_seconds_by_day(
        db,
        employee_id=employee_id,
        week_start=week_start,
        as_of_date=effective_as_of_date,
    )

    policy_status = evaluate_weekly_policy(
        week_start=week_start,
        as_of_date=effective_as_of_date,
        daily_seconds=daily_seconds,
    )

    final_due = is_final_evaluation_due(
        week_start=week_start,
        now=now,
    )

    decisions = decide_notifications(
        policy_status=policy_status,
        as_of_date=effective_as_of_date,
        is_final_evaluation_due=final_due,
    )

    created_notifications = []

    for decision in decisions:
        notification = create_notification(
            db,
            employee_id=employee.id,
            week_start=week_start,
            notification_type=decision.notification_type,
            milestone_key=decision.milestone_key,
            recipient_email=employee.email,
            scheduled_at=now.astimezone(timezone.utc),
            tenant_id=employee.tenant_id,
        )
        created_notifications.append(notification)

    return {
        "employee_id": employee.id,
        "week_start": week_start,
        "as_of_date": effective_as_of_date,
        "policy_status": policy_status,
        "decisions": decisions,
        "notifications": created_notifications,
    }
