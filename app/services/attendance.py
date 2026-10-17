
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.schemas.attendance import DailyAttendanceResponse,WeeklyAttendanceResponse

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceSession
from app.services.cache import invalidate_employee_reports
from app.services.employees import get_employee


class EmployeeNotFoundError(Exception):
    pass


class InactiveEmployeeError(Exception):
    pass


class ActiveAttendanceSessionError(Exception):
    pass


def check_in_employee(
    db: Session,
    employee_id: int,
    tenant_id: int,
) -> AttendanceSession:
    employee = get_employee(db, employee_id, tenant_id)

    if employee is None:
        raise EmployeeNotFoundError

    if not employee.is_active:
        raise InactiveEmployeeError

    existing_session = db.scalar(
        select(AttendanceSession).where(
            AttendanceSession.employee_id == employee_id,
            AttendanceSession.checked_out_at.is_(None),
        )
    )

    if existing_session is not None:
        raise ActiveAttendanceSessionError

    attendance = AttendanceSession(
        tenant_id=tenant_id,
        employee_id=employee_id,
        checked_in_at=datetime.now(timezone.utc),
    )

    db.add(attendance)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        original_error = exc.orig
        diagnostic = getattr(original_error, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)

        if constraint_name == "uq_attendance_one_active_session_per_employee":
            raise ActiveAttendanceSessionError from exc

        raise

    db.refresh(attendance)
    invalidate_employee_reports(tenant_id, employee_id)

    return attendance


class NoActiveAttendanceSessionError(Exception):
    pass


def check_out_employee(
    db: Session,
    employee_id: int,
    tenant_id: int,
) -> AttendanceSession:
    employee = get_employee(db, employee_id, tenant_id)

    if employee is None:
        raise EmployeeNotFoundError

    if not employee.is_active:
        raise InactiveEmployeeError

    # Lock the active session while we close it.
    attendance = db.scalar(
        select(AttendanceSession)
        .where(
            AttendanceSession.employee_id == employee_id,
            AttendanceSession.checked_out_at.is_(None),
        )
        .with_for_update()
    )

    if attendance is None:
        raise NoActiveAttendanceSessionError

    checkout_time = datetime.now(timezone.utc)

    if checkout_time < attendance.checked_in_at:
        raise ValueError("Checkout time cannot precede check-in time.")

    attendance.checked_out_at = checkout_time

    db.commit()
    db.refresh(attendance)
    invalidate_employee_reports(tenant_id, employee_id)

    return attendance


def get_daily_attendance(
    db: Session,
    employee_id: int,
    attendance_date: date,
    tenant_id: int,
) -> DailyAttendanceResponse:
    employee = get_employee(db, employee_id, tenant_id)

    if employee is None:
        raise EmployeeNotFoundError

    company_timezone = ZoneInfo(settings.company_timezone)

    local_start = datetime.combine(
        attendance_date,
        time.min,
        tzinfo=company_timezone,
    )
    local_end = datetime.combine(
        attendance_date + timedelta(days=1),
        time.min,
        tzinfo=company_timezone,
    )

    day_start_utc = local_start.astimezone(timezone.utc)
    day_end_utc = local_end.astimezone(timezone.utc)

    sessions = db.scalars(
        select(AttendanceSession).where(
            AttendanceSession.employee_id == employee_id,
            AttendanceSession.checked_out_at.is_not(None),
            AttendanceSession.checked_in_at < day_end_utc,
            AttendanceSession.checked_out_at > day_start_utc,
        )
    ).all()

    total_seconds = 0

    for session in sessions:
        session_start = max(
            session.checked_in_at,
            day_start_utc,
        )
        session_end = min(
            session.checked_out_at,
            day_end_utc,
        )

        if session_end > session_start:
            total_seconds += int(
                (session_end - session_start).total_seconds()
            )

    total_hours = round(total_seconds / 3600, 2)
    daily_target_hours = 5.0

    return DailyAttendanceResponse(
        employee_id=employee_id,
        attendance_date=attendance_date,
        completed_sessions=len(sessions),
        total_seconds=total_seconds,
        total_hours=total_hours,
        daily_target_hours=daily_target_hours,
        meets_daily_target=total_seconds >= 5 * 3600,
    )


def get_weekly_attendance(
    db: Session,
    employee_id: int,
    week_date: date,
    tenant_id: int,
) -> WeeklyAttendanceResponse:
    employee = get_employee(db, employee_id, tenant_id)

    if employee is None:
        raise EmployeeNotFoundError

    company_timezone = ZoneInfo(settings.company_timezone)

    # Find Monday and the following Monday in local time.
    week_start = week_date - timedelta(days=week_date.weekday())
    week_end = week_start + timedelta(days=6)

    week_start_local = datetime.combine(
        week_start, time.min, tzinfo=company_timezone
    )
    next_week_start_local = datetime.combine(
        week_start + timedelta(days=7),
        time.min,
        tzinfo=company_timezone,
    )

    week_start_utc = week_start_local.astimezone(timezone.utc)
    next_week_start_utc = next_week_start_local.astimezone(timezone.utc)

    sessions = db.scalars(
        select(AttendanceSession).where(
            AttendanceSession.employee_id == employee_id,
            AttendanceSession.checked_out_at.is_not(None),
            AttendanceSession.checked_in_at < next_week_start_utc,
            AttendanceSession.checked_out_at > week_start_utc,
        )
    ).all()

    # Accumulate exact seconds for each local calendar day.
    daily_seconds: dict[date, int] = {}

    for session in sessions:
        session_start = max(
            session.checked_in_at,
            week_start_utc,
        )
        session_end = min(
            session.checked_out_at,
            next_week_start_utc,
        )

        if session_end <= session_start:
            continue

        # Split sessions at local midnight. This also handles
        # weeks with daylight-saving transitions in other timezones.
        cursor = session_start

        while cursor < session_end:
            local_cursor = cursor.astimezone(company_timezone)
            local_day = local_cursor.date()

            next_midnight_local = datetime.combine(
                local_day + timedelta(days=1),
                time.min,
                tzinfo=company_timezone,
            )
            next_midnight_utc = next_midnight_local.astimezone(timezone.utc)

            segment_end = min(session_end, next_midnight_utc)

            seconds = int((segment_end - cursor).total_seconds())
            daily_seconds[local_day] = (
                daily_seconds.get(local_day, 0) + seconds
            )

            cursor = segment_end

    total_seconds = sum(daily_seconds.values())
    qualifying_days = sum(
        1 for seconds in daily_seconds.values()
        if seconds >= 5 * 3600
    )

    meets_daily_requirements = qualifying_days >= 3
    meets_weekly_hours_requirement = total_seconds >= 15 * 3600

    return WeeklyAttendanceResponse(
        employee_id=employee_id,
        week_start=week_start,
        week_end=week_end,
        qualifying_days=qualifying_days,
        total_seconds=total_seconds,
        total_hours=round(total_seconds / 3600, 2),
        minimum_qualifying_days=3,
        minimum_daily_hours=5.0,
        minimum_weekly_hours=15.0,
        meets_daily_requirements=meets_daily_requirements,
        meets_weekly_hours_requirement=meets_weekly_hours_requirement,
        is_compliant=(
            meets_daily_requirements
            and meets_weekly_hours_requirement
        ),
    )


