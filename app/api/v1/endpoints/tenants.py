from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.tenant import Tenant
from app.models.user_account import UserAccount
from app.schemas.tenant import TenantResponse

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/current", response_model=TenantResponse)
def read_current_tenant(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = db.get(Tenant, current_user.tenant_id)

    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    return tenant
