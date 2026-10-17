from datetime import date
from unittest.mock import MagicMock, patch

from app.schemas.reports import EmployeeAttendanceReportResponse
from app.services.cache import (
    get_cached_report,
    invalidate_employee_reports,
    report_cache_key,
    set_cached_report,
)


def make_report() -> EmployeeAttendanceReportResponse:
    return EmployeeAttendanceReportResponse(
        employee_id=1,
        employee_name="Test Employee",
        employee_email="report-test@example.com",
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 18),
        days_in_range=7,
        daily_records=[],
        total_seconds=0,
        total_hours=0.0,
        qualifying_days=0,
        complete_weeks_evaluated=0,
        weekly_records=[],
    )


def test_report_cache_key_includes_employee_and_dates():
    assert report_cache_key(
        12,
        date(2026, 10, 1),
        date(2026, 10, 7),
    ) == "attendance:report:12:2026-10-01:2026-10-07"


@patch("app.services.cache.get_redis")
def test_get_cached_report_returns_none_when_missing(get_redis):
    client = MagicMock()
    client.get.return_value = None
    get_redis.return_value = client

    assert get_cached_report(1, date(2026, 10, 12), date(2026, 10, 18)) is None


@patch("app.services.cache.get_redis")
def test_set_and_get_cached_report(get_redis):
    report = make_report()
    store: dict[str, str] = {}

    client = MagicMock()
    client.setex.side_effect = lambda key, _ttl, value: store.update({key: value})
    client.get.side_effect = lambda key: store.get(key)
    get_redis.return_value = client

    set_cached_report(report)
    cached = get_cached_report(1, date(2026, 10, 12), date(2026, 10, 18))

    assert cached is not None
    assert cached.employee_id == 1
    assert cached.employee_name == "Test Employee"


@patch("app.services.cache.get_redis")
def test_invalidate_employee_reports_deletes_matching_keys(get_redis):
    client = MagicMock()
    client.scan_iter.return_value = [
        "attendance:report:1:2026-10-12:2026-10-18",
        "attendance:report:1:2026-10-01:2026-10-31",
    ]
    get_redis.return_value = client

    invalidate_employee_reports(1)

    client.delete.assert_called_once()
    deleted_keys = client.delete.call_args.args
    assert "attendance:report:1:2026-10-12:2026-10-18" in deleted_keys
