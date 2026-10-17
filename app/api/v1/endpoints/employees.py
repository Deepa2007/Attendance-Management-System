from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.db.database import get_db
from app.models.user_account import UserAccount
from app.schemas.employee import EmployeeCreate, EmployeeResponse
from app.services.employees import (
    DuplicateEmployeeEmailError,
    create_employee,
    get_employee,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    admin: UserAccount = Depends(require_admin),
):
    try:
        return create_employee(
            db,
            employee_data,
            tenant_id=admin.tenant_id,
        )
    except DuplicateEmployeeEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An employee with this email already exists.",
        )


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
)
def read_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    employee = get_employee(
        db,
        employee_id,
        tenant_id=current_user.tenant_id,
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    return employee
