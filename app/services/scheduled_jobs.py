from datetime import date, datetime, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.employee import Employee
from app.services.notification_workflow import process_employee_week
from app.services.notification_schedule import is_final_evaluation_due
from app.services.email_provider import FakeEmailProvider
from app.services.notification_delivery import (
    deliver_pending_notifications,
)

logger = logging.getLogger(__name__)

COMPANY_TIMEZONE = ZoneInfo(settings.company_timezone)
email_provider = FakeEmailProvider()

def _get_local_date_and_now() -> tuple[date, datetime]:
    """Return the current company-local date and timezone-aware UTC time."""
    now = datetime.now(timezone.utc)
    local_date = now.astimezone(COMPANY_TIMEZONE).date()
    return local_date, now


def _process_week_for_active_employees(
    *,
    week_start: date,
    as_of_date: date,
    now: datetime,
) -> None:
    """Evaluate every active employee and isolate individual failures."""

    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    processed_count = 0
    failed_count = 0

    with SessionLocal() as db:
        employee_ids = db.scalars(
            select(Employee.id)
            .where(Employee.is_active.is_(True))
            .order_by(Employee.id)
        ).all()

        logger.info(
            "Starting attendance notification check: week_start=%s, "
            "as_of_date=%s, active_employees=%s",
            week_start,
            as_of_date,
            len(employee_ids),
        )

        for employee_id in employee_ids:
            try:
                result = process_employee_week(
                    db,
                    employee_id=employee_id,
                    week_start=week_start,
                    as_of_date=as_of_date,
                    now=now,
                )

                processed_count += 1

                logger.info(
                    "Processed attendance notifications: employee_id=%s, "
                    "notifications_created=%s",
                    employee_id,
                    len(result["notifications"]),
                )

            except Exception:
                db.rollback()
                failed_count += 1

                logger.exception(
                    "Failed to process attendance notifications "
                    "for employee_id=%s, week_start=%s",
                    employee_id,
                    week_start,
                )

    logger.info(
        "Attendance notification check completed: week_start=%s, "
        "processed=%s, failed=%s",
        week_start,
        processed_count,
        failed_count,
    )

def run_progress_notification_check() -> None:
    """Evaluate the current attendance week for progress notifications."""

    local_today, now = _get_local_date_and_now()
    week_start = local_today - timedelta(days=local_today.weekday())

    _process_week_for_active_employees(
        week_start=week_start,
        as_of_date=local_today,
        now=now,
    )

    _deliver_pending_emails()


def run_final_weekly_notification_check() -> None:
    """Evaluate the previous attendance week after the grace period."""

    local_today, now = _get_local_date_and_now()

    current_week_start = local_today - timedelta(
        days=local_today.weekday()
    )
    previous_week_start = current_week_start - timedelta(days=7)

    if not is_final_evaluation_due(
        week_start=previous_week_start,
        now=now,
    ):
        logger.info(
            "Final weekly evaluation is not due yet: week_start=%s",
            previous_week_start,
        )
        return

    previous_week_end = previous_week_start + timedelta(days=6)

    _process_week_for_active_employees(
        week_start=previous_week_start,
        as_of_date=previous_week_end,
        now=now,
    )
    _deliver_pending_emails()


def _deliver_pending_emails() -> None:
    """Deliver due notifications using the configured email provider."""

    with SessionLocal() as db:
        result = deliver_pending_notifications(
            db,
            provider=email_provider,
        )

    logger.info(
        "Notification delivery completed: claimed=%s, sent=%s, failed=%s",
        result["claimed"],
        result["sent"],
        result["failed"],
    )