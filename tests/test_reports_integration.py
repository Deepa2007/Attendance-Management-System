from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.db.database import engine
from app.models.attendance import AttendanceSession
from app.models.employee import Employee
from app.models.tenant import Tenant
from app.services.reports import get_employee_attendance_report
from app.services.reports import InvalidReportDateRangeError

@pytest.fixture
def report_test_data():
    # Never run these integration tests against another database.
    if engine.url.database != "attendance_test_db":
        pytest.fail(
            "Safety check failed: integration tests require "
            "the attendance_test_db database. "
            f"Current database: {engine.url.database!r}"
        )

    connection = engine.connect()
    transaction = connection.begin()
    db = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
    )

    tenant = Tenant(
        name="Integration Tenant",
        slug=f"int-{uuid4().hex[:12]}",
        is_active=True,
    )
    db.add(tenant)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        full_name="Integration Test Employee",
        email=f"integration-{uuid4().hex}@example.com",
    )

    try:
        db.add(employee)
        db.flush()

        yield db, employee

    finally:
        # Roll back every change made by this test.
        db.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def local_time(day: date, hour: int, minute: int = 0) -> datetime:
    """Convert company-local time to a UTC timestamp."""
    tz = ZoneInfo(settings.company_timezone)

    local_dt = datetime(
        day.year,
        day.month,
        day.day,
        hour,
        minute,
        tzinfo=tz,
    )

    return local_dt.astimezone(timezone.utc)


def add_session(db, employee, start, end):
    session = AttendanceSession(
        tenant_id=employee.tenant_id,
        employee_id=employee.id,
        checked_in_at=start,
        checked_out_at=end,
    )
    db.add(session)
    db.flush()
    return session


def test_real_postgres_daily_hours(report_test_data):
    db, employee = report_test_data
    day = date(2026, 10, 12)

    add_session(
        db,
        employee,
        local_time(day, 9),
        local_time(day, 14),
    )

    report = get_employee_attendance_report(
        db,
        employee.id,
        day,
        day,
    )

    assert report.employee_id == employee.id
    assert report.daily_records[0].total_seconds == 5 * 3600
    assert report.daily_records[0].meets_daily_target is True


def test_real_postgres_weekly_compliance(report_test_data):
    db, employee = report_test_data
    monday = date(2026, 10, 12)

    for offset in range(3):
        day = date.fromordinal(monday.toordinal() + offset)
        add_session(
            db,
            employee,
            local_time(day, 9),
            local_time(day, 14),
        )

    report = get_employee_attendance_report(
        db,
        employee.id,
        monday,
        date(2026, 10, 18),
    )

    assert report.complete_weeks_evaluated == 1

    week = report.weekly_records[0]
    assert week.qualifying_days == 3
    assert week.total_seconds == 15 * 3600
    assert week.is_compliant is True


def test_real_postgres_excludes_incomplete_session(report_test_data):
    db, employee = report_test_data
    day = date(2026, 10, 12)

    add_session(
        db,
        employee,
        local_time(day, 9),
        None,
    )

    report = get_employee_attendance_report(
        db,
        employee.id,
        day,
        day,
    )

    assert report.daily_records[0].total_seconds == 0
    assert report.qualifying_days == 0


def test_real_postgres_splits_overnight_session(report_test_data):
    db, employee = report_test_data
    day = date(2026, 10, 12)
    next_day = date(2026, 10, 13)

    add_session(
        db,
        employee,
        local_time(day, 22),
        local_time(next_day, 2),
    )

    report = get_employee_attendance_report(
        db,
        employee.id,
        day,
        next_day,
    )

    assert report.daily_records[0].total_seconds == 2 * 3600
    assert report.daily_records[1].total_seconds == 2 * 3600
    assert report.total_seconds == 4 * 3600


def test_real_postgres_rejects_reversed_date_range(report_test_data):
    db, employee = report_test_data

    with pytest.raises(InvalidReportDateRangeError):
        get_employee_attendance_report(
            db,
            employee.id,
            date(2026, 10, 18),
            date(2026, 10, 12),
        )

def test_postgres_rejects_checkout_before_checkin(report_test_data):
    db, employee = report_test_data
    day = date(2026, 10, 12)

    invalid_session = AttendanceSession(
        employee_id=employee.id,
        checked_in_at=local_time(day, 14),
        checked_out_at=local_time(day, 9),
    )
    db.add(invalid_session)

    with pytest.raises(IntegrityError):
        db.flush()

    db.rollback()

def test_postgres_rejects_second_active_session(report_test_data):
    db, employee = report_test_data
    day = date(2026, 10, 12)

    first_session = AttendanceSession(
        employee_id=employee.id,
        checked_in_at=local_time(day, 9),
        checked_out_at=None,
    )
    db.add(first_session)
    db.flush()

    second_session = AttendanceSession(
        employee_id=employee.id,
        checked_in_at=local_time(day, 10),
        checked_out_at=None,
    )
    db.add(second_session)

    with pytest.raises(IntegrityError):
        db.flush()

    db.rollback()

def test_postgres_rejects_overlapping_completed_sessions(report_test_data):
    db, employee = report_test_data
    day = date(2026, 10, 12)

    first_session = AttendanceSession(
        employee_id=employee.id,
        checked_in_at=local_time(day, 9),
        checked_out_at=local_time(day, 14),
    )
    db.add(first_session)
    db.flush()

    overlapping_session = AttendanceSession(
        employee_id=employee.id,
        checked_in_at=local_time(day, 11),
        checked_out_at=local_time(day, 13),
    )
    db.add(overlapping_session)

    with pytest.raises(IntegrityError):
        db.flush()

    db.rollback()


def test_postgres_allows_adjacent_sessions(report_test_data):
    db, employee = report_test_data
    day = date(2026, 10, 12)

    first_session = AttendanceSession(
        employee_id=employee.id,
        checked_in_at=local_time(day, 9),
        checked_out_at=local_time(day, 12),
    )
    second_session = AttendanceSession(
        employee_id=employee.id,
        checked_in_at=local_time(day, 12),
        checked_out_at=local_time(day, 15),
    )

    db.add_all([first_session, second_session])
    db.flush()

    assert first_session.id is not None
    assert second_session.id is not None