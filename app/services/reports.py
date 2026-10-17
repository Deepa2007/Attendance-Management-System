
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attendance import AttendanceSession
from app.models.employee import Employee
from app.schemas.reports import (
    DailyReportItem,
    EmployeeAttendanceReportResponse,
    WeeklyReportItem,
)


class ReportEmployeeNotFoundError(Exception):
    """Raised when the requested employee does not exist."""


class InvalidReportDateRangeError(Exception):
    """Raised when the report date range is invalid."""


def get_employee_attendance_report(
    db: Session,
    employee_id: int,
    start_date: date,
    end_date: date,
    tenant_id: int | None = None,
) -> EmployeeAttendanceReportResponse:
    """Build an employee attendance report for an inclusive date range."""

    if end_date < start_date:
        raise InvalidReportDateRangeError(
            "end_date must be on or after start_date"
        )

    # Prevent accidental requests for excessively large date ranges.
    if (end_date - start_date).days > 365:
        raise InvalidReportDateRangeError(
            "The report date range cannot exceed 366 calendar days"
        )

    employee = db.get(Employee, employee_id)

    if employee is None:
        raise ReportEmployeeNotFoundError(
            f"Employee {employee_id} was not found"
        )

    employee_tenant_id = getattr(employee, "tenant_id", tenant_id)
    if (
        tenant_id is not None
        and employee_tenant_id is not None
        and employee_tenant_id != tenant_id
    ):
        raise ReportEmployeeNotFoundError(
            f"Employee {employee_id} was not found"
        )

    tz = ZoneInfo(settings.company_timezone)

    # Convert local midnight boundaries to UTC for database filtering.
    local_start = datetime.combine(
        start_date, time.min, tzinfo=tz
    )
    local_end_exclusive = datetime.combine(
        end_date + timedelta(days=1), time.min, tzinfo=tz
    )

    utc_start = local_start.astimezone(timezone.utc)
    utc_end_exclusive = local_end_exclusive.astimezone(timezone.utc)

    sessions = db.scalars(
        select(AttendanceSession)
        .where(
            AttendanceSession.employee_id == employee_id,
            AttendanceSession.checked_out_at.is_not(None),
            AttendanceSession.checked_in_at < utc_end_exclusive,
            AttendanceSession.checked_out_at > utc_start,
        )
        .order_by(AttendanceSession.checked_in_at)
    ).all()

    # Store completed seconds by local calendar day.
    seconds_by_day: dict[date, int] = {}
    session_count_by_day: dict[date, int] = {}

    for session in sessions:
        session_start = session.checked_in_at
        session_end = session.checked_out_at

        if session_end is None:
            continue

        # Split sessions at local midnight so overnight sessions
        # contribute the correct time to each calendar day.
        cursor = max(
            session_start,
            utc_start,
        )

        session_end_utc = min(
            session_end,
            utc_end_exclusive,
        )

        while cursor < session_end_utc:
            local_cursor = cursor.astimezone(tz)
            next_local_midnight = datetime.combine(
                local_cursor.date() + timedelta(days=1),
                time.min,
                tzinfo=tz,
            )
            next_boundary_utc = next_local_midnight.astimezone(
                timezone.utc
            )

            segment_end = min(
                session_end_utc,
                next_boundary_utc,
            )

            seconds = int((segment_end - cursor).total_seconds())
            current_day = local_cursor.date()

            seconds_by_day[current_day] = (
                seconds_by_day.get(current_day, 0) + seconds
            )
            session_count_by_day[current_day] = (
                session_count_by_day.get(current_day, 0) + 1
            )

            cursor = segment_end

    daily_records: list[DailyReportItem] = []
    daily_seconds: dict[date, int] = {}

    current_date = start_date

    while current_date <= end_date:
        total_seconds = seconds_by_day.get(current_date, 0)
        total_hours = round(total_seconds / 3600, 2)

        daily_seconds[current_date] = total_seconds

        daily_records.append(
            DailyReportItem(
                attendance_date=current_date,
                completed_sessions=session_count_by_day.get(
                    current_date, 0
                ),
                total_seconds=total_seconds,
                total_hours=total_hours,
                daily_target_hours=5.0,
                meets_daily_target=total_seconds >= 5 * 3600,
            )
        )

        current_date += timedelta(days=1)

    total_seconds = sum(daily_seconds.values())
    qualifying_days = sum(
        1
        for seconds in daily_seconds.values()
        if seconds >= 5 * 3600
    )

    weekly_records: list[WeeklyReportItem] = []

    # Only evaluate complete Monday-Sunday weeks fully inside
    # the selected report range.
    week_start = start_date + timedelta(
        days=(7 - start_date.weekday()) % 7
    )

    while week_start + timedelta(days=6) <= end_date:
        week_end = week_start + timedelta(days=6)

        week_total_seconds = sum(
            daily_seconds.get(week_start + timedelta(days=offset), 0)
            for offset in range(7)
        )

        week_qualifying_days = sum(
            1
            for offset in range(7)
            if daily_seconds.get(
                week_start + timedelta(days=offset), 0
            ) >= 5 * 3600
        )

        meets_daily_requirements = week_qualifying_days >= 3
        meets_weekly_hours_requirement = (
            week_total_seconds >= 15 * 3600
        )

        weekly_records.append(
            WeeklyReportItem(
                week_start=week_start,
                week_end=week_end,
                qualifying_days=week_qualifying_days,
                total_seconds=week_total_seconds,
                total_hours=round(
                    week_total_seconds / 3600, 2
                ),
                minimum_qualifying_days=3,
                minimum_daily_hours=5.0,
                minimum_weekly_hours=15.0,
                meets_daily_requirements=meets_daily_requirements,
                meets_weekly_hours_requirement=(
                    meets_weekly_hours_requirement
                ),
                is_compliant=(
                    meets_daily_requirements
                    and meets_weekly_hours_requirement
                ),
            )
        )

        week_start += timedelta(days=7)

    return EmployeeAttendanceReportResponse(
        employee_id=employee.id,
        employee_name=employee.full_name,
        employee_email=employee.email,
        start_date=start_date,
        end_date=end_date,
        days_in_range=(end_date - start_date).days + 1,
        daily_records=daily_records,
        total_seconds=total_seconds,
        total_hours=round(total_seconds / 3600, 2),
        qualifying_days=qualifying_days,
        complete_weeks_evaluated=len(weekly_records),
        weekly_records=weekly_records,
    )
