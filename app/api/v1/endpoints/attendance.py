from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user_account import UserAccount
from app.schemas.attendance import (
    AttendanceSessionResponse,
    CheckInRequest,
    CheckOutRequest,
    DailyAttendanceResponse,
    WeeklyAttendanceResponse,
)
from app.services.attendance import (
    ActiveAttendanceSessionError,
    EmployeeNotFoundError,
    InactiveEmployeeError,
    NoActiveAttendanceSessionError,
    check_in_employee,
    check_out_employee,
    get_daily_attendance,
    get_weekly_attendance,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post(
    "/check-in",
    response_model=AttendanceSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def check_in(
    request: CheckInRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    try:
        return check_in_employee(
            db=db,
            employee_id=request.employee_id,
            tenant_id=current_user.tenant_id,
        )
    except EmployeeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )
    except InactiveEmployeeError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inactive employees cannot check in.",
        )
    except ActiveAttendanceSessionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee already has an active attendance session.",
        )


@router.post(
    "/check-out",
    response_model=AttendanceSessionResponse,
)
def check_out(
    request: CheckOutRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    try:
        return check_out_employee(
            db=db,
            employee_id=request.employee_id,
            tenant_id=current_user.tenant_id,
        )
    except EmployeeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )
    except InactiveEmployeeError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inactive employees cannot check out.",
        )
    except NoActiveAttendanceSessionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee has no active attendance session.",
        )


@router.get(
    "/daily/{employee_id}",
    response_model=DailyAttendanceResponse,
)
def daily_attendance(
    employee_id: int,
    attendance_date: date,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    try:
        return get_daily_attendance(
            db=db,
            employee_id=employee_id,
            attendance_date=attendance_date,
            tenant_id=current_user.tenant_id,
        )
    except EmployeeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )


@router.get(
    "/weekly/{employee_id}",
    response_model=WeeklyAttendanceResponse,
)
def weekly_attendance(
    employee_id: int,
    week_date: date,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    try:
        return get_weekly_attendance(
            db=db,
            employee_id=employee_id,
            week_date=week_date,
            tenant_id=current_user.tenant_id,
        )
    except EmployeeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )
