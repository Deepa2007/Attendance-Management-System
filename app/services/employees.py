from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate


class DuplicateEmployeeEmailError(Exception):
    """Raised when an employee email already exists in this tenant."""


def create_employee(
    db: Session,
    employee_data: EmployeeCreate,
    tenant_id: int,
) -> Employee:
    employee = Employee(
        tenant_id=tenant_id,
        full_name=employee_data.full_name,
        email=str(employee_data.email),
    )

    db.add(employee)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmployeeEmailError from exc

    db.refresh(employee)
    return employee


def get_employee(
    db: Session,
    employee_id: int,
    tenant_id: int,
) -> Employee | None:
    return db.scalar(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.tenant_id == tenant_id,
        )
    )
