from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.database import SessionLocal, engine
from app.main import app
from app.models.tenant import Tenant
from app.models.user_account import UserAccount


def test_employee_cannot_access_admin_reports():
    # Safety check: never create test data in the main database.
    if engine.url.database != "attendance_test_db":
        pytest.fail(
            "Authorization tests require attendance_test_db. "
            f"Current database: {engine.url.database!r}"
        )

    db = SessionLocal()
    user = None
    tenant = None

    try:
        tenant = Tenant(
            name="Employee Auth Tenant",
            slug=f"emp-{uuid4().hex[:12]}",
            is_active=True,
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        user = UserAccount(
            tenant_id=tenant.id,
            email=f"employee-{uuid4().hex}@example.com",
            hashed_password=hash_password("Temporary-Test-Password-123!"),
            role="employee",
            employee_id=None,
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(
            subject=str(user.id),
            tenant_id=tenant.id,
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/reports/employees/1",
                params={
                    "start_date": "2026-10-12",
                    "end_date": "2026-10-18",
                },
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "Administrator access required"

    finally:
        if user is not None:
            db.delete(user)
            db.commit()
        if tenant is not None:
            db.delete(tenant)
            db.commit()

        db.close()

def test_admin_can_access_reports():
    if engine.url.database != "attendance_test_db":
        pytest.fail(
            "Authorization tests require attendance_test_db. "
            f"Current database: {engine.url.database!r}"
        )

    db = SessionLocal()
    user = None
    tenant = None

    try:
        tenant = Tenant(
            name="Admin Auth Tenant",
            slug=f"adm-{uuid4().hex[:12]}",
            is_active=True,
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        user = UserAccount(
            tenant_id=tenant.id,
            email=f"admin-{uuid4().hex}@example.com",
            hashed_password=hash_password("Temporary-Test-Password-123!"),
            role="admin",
            employee_id=None,
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(
            subject=str(user.id),
            tenant_id=tenant.id,
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/reports/employees/1",
                params={
                    "start_date": "2026-10-12",
                    "end_date": "2026-10-18",
                },
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        # Employee 1 may or may not exist; both outcomes prove
        # that the administrator passed authorization.
        assert response.status_code in (200, 404)

    finally:
        if user is not None:
            db.delete(user)
            db.commit()
        if tenant is not None:
            db.delete(tenant)
            db.commit()

        db.close()