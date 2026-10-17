from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.services.scheduled_jobs import (
    run_progress_notification_check,
    run_final_weekly_notification_check,
)
company_timezone = ZoneInfo(settings.company_timezone)

scheduler = BackgroundScheduler(
    timezone=company_timezone,
    job_defaults={
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 3600,
    },
)

def register_jobs() -> None:
    """Register recurring attendance notification checks."""

    scheduler.add_job(
        run_progress_notification_check,
        trigger=CronTrigger(
            day_of_week="wed,fri",
            hour=9,
            minute=0,
            timezone=company_timezone,
        ),
        id="attendance_progress_check",
        replace_existing=True,
    )

    scheduler.add_job(
        run_final_weekly_notification_check,
        trigger=CronTrigger(
            day_of_week="tue",
            hour=0,
            minute=5,
            timezone=company_timezone,
        ),
        id="attendance_final_weekly_check",
        replace_existing=True,
    )