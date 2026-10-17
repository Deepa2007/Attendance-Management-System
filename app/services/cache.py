import logging
from datetime import date

from redis.exceptions import RedisError

from app.core.config import settings
from app.db.redis import get_redis
from app.schemas.reports import EmployeeAttendanceReportResponse

logger = logging.getLogger(__name__)

REPORT_CACHE_PREFIX = "attendance:report"


def report_cache_key(
    employee_id: int,
    start_date: date,
    end_date: date,
) -> str:
    return (
        f"{REPORT_CACHE_PREFIX}:{employee_id}:"
        f"{start_date.isoformat()}:{end_date.isoformat()}"
    )


def get_cached_report(
    employee_id: int,
    start_date: date,
    end_date: date,
) -> EmployeeAttendanceReportResponse | None:
    """Return a cached attendance report, or None if missing or Redis is down."""
    try:
        payload = get_redis().get(
            report_cache_key(employee_id, start_date, end_date)
        )
    except RedisError:
        logger.warning("Failed to read report cache", exc_info=True)
        return None

    if not payload:
        return None

    return EmployeeAttendanceReportResponse.model_validate_json(payload)


def set_cached_report(
    report: EmployeeAttendanceReportResponse,
) -> None:
    """Store an attendance report in Redis. Failures are ignored."""
    try:
        get_redis().setex(
            report_cache_key(
                report.employee_id,
                report.start_date,
                report.end_date,
            ),
            settings.redis_cache_ttl_seconds,
            report.model_dump_json(),
        )
    except RedisError:
        logger.warning("Failed to write report cache", exc_info=True)


def invalidate_employee_reports(employee_id: int) -> None:
    """Drop cached reports for an employee after attendance changes."""
    pattern = f"{REPORT_CACHE_PREFIX}:{employee_id}:*"

    try:
        client = get_redis()
        keys = list(client.scan_iter(match=pattern, count=100))
        if keys:
            client.delete(*keys)
    except RedisError:
        logger.warning("Failed to invalidate report cache", exc_info=True)
