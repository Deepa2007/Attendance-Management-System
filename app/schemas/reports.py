from datetime import date

from pydantic import BaseModel


class DailyReportItem(BaseModel):
    attendance_date: date
    completed_sessions: int
    total_seconds: int
    total_hours: float
    daily_target_hours: float
    meets_daily_target: bool


class WeeklyReportItem(BaseModel):
    week_start: date
    week_end: date
    qualifying_days: int
    total_seconds: int
    total_hours: float
    minimum_qualifying_days: int
    minimum_daily_hours: float
    minimum_weekly_hours: float
    meets_daily_requirements: bool
    meets_weekly_hours_requirement: bool
    is_compliant: bool


class EmployeeAttendanceReportResponse(BaseModel):
    employee_id: int
    employee_name: str
    employee_email: str

    start_date: date
    end_date: date
    days_in_range: int

    daily_records: list[DailyReportItem]

    total_seconds: int
    total_hours: float
    qualifying_days: int

    complete_weeks_evaluated: int
    weekly_records: list[WeeklyReportItem]
