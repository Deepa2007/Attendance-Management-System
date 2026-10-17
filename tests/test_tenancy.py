from datetime import date
from types import SimpleNamespace

from app.services.cache import report_cache_key
from app.services.reports import (
    ReportEmployeeNotFoundError,
    get_employee_attendance_report,
)
import pytest
from unittest.mock import MagicMock


def test_redis_keys_do_not_collide_across_tenants():
    start = date(2026, 10, 12)
    end = date(2026, 10, 18)

    key_a = report_cache_key(1, 10, start, end)
    key_b = report_cache_key(2, 10, start, end)

    assert key_a != key_b
    assert ":1:10:" in key_a
    assert ":2:10:" in key_b


def test_report_hides_employees_from_other_tenants():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(
        id=1,
        tenant_id=2,
        full_name="Other Tenant",
        email="other@example.com",
    )

    with pytest.raises(ReportEmployeeNotFoundError):
        get_employee_attendance_report(
            db,
            1,
            date(2026, 10, 12),
            date(2026, 10, 12),
            tenant_id=1,
        )
