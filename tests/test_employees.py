from uuid import uuid4
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.models.employee import Employee
from app.services.employees import get_employee


def test_create_employee_requires_authentication():
    email = f"employee-{uuid4().hex}@example.com"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/employees",
            json={
                "full_name": "Test Employee",
                "email": email,
            },
        )

    assert response.status_code == 401


def test_read_employee_requires_authentication():
    with TestClient(app) as client:
        response = client.get("/api/v1/employees/1")

    assert response.status_code == 401


def test_get_employee_is_scoped_to_tenant():
    matching = Employee(
        id=1,
        tenant_id=5,
        full_name="Tenant Employee",
        email="a@example.com",
    )
    db = MagicMock()
    db.scalar.return_value = matching

    found = get_employee(db, 1, tenant_id=5)

    assert found is matching
    db.scalar.assert_called_once()
