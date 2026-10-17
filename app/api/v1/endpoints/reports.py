
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.database import get_db
from app.models.user_account import UserAccount
from app.schemas.reports import EmployeeAttendanceReportResponse
from app.services.cache import get_cached_report, set_cached_report
from app.services.reports import (
    InvalidReportDateRangeError,
    ReportEmployeeNotFoundError,
    get_employee_attendance_report,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/employees/{employee_id}",
    response_model=EmployeeAttendanceReportResponse,
)
def employee_attendance_report(
    employee_id: int,
    start_date: date = Query(..., description="First date, inclusive (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Last date, inclusive (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    admin: UserAccount = Depends(require_admin),
) -> EmployeeAttendanceReportResponse:
    """Return an employee attendance report. Admin access required."""

    cached = get_cached_report(
        admin.tenant_id,
        employee_id,
        start_date,
        end_date,
    )
    if cached is not None:
        return cached

    try:
        report = get_employee_attendance_report(
            db=db,
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            tenant_id=admin.tenant_id,
        )
    except ReportEmployeeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidReportDateRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    set_cached_report(admin.tenant_id, report)
    return report
