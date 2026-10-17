from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckInRequest(BaseModel):
    employee_id: int = Field(gt=0)


class CheckOutRequest(BaseModel):
    employee_id: int = Field(gt=0)


class AttendanceSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    checked_in_at: datetime
    checked_out_at: datetime | None
    created_at: datetime


class DailyAttendanceResponse(BaseModel):
    employee_id: int
    attendance_date: date
    completed_sessions: int
    total_seconds: int
    total_hours: float
    daily_target_hours: float
    meets_daily_target: bool


class WeeklyAttendanceResponse(BaseModel):
    employee_id: int
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
