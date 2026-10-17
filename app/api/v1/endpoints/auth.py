from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.security import create_access_token, verify_password
from app.core.tenancy import TENANT_SLUG_HEADER
from app.db.database import get_db
from app.models.tenant import Tenant
from app.models.user_account import UserAccount
from app.schemas.auth import TokenResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_tenant_slug: str | None = Header(default=None, alias=TENANT_SLUG_HEADER),
) -> TokenResponse:
    tenant_slug = (x_tenant_slug or form_data.client_id or "").strip().lower()

    if not tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Tenant slug is required. Send it in the "
                f"{TENANT_SLUG_HEADER} header."
            ),
        )

    tenant = db.scalar(
        select(Tenant).where(
            Tenant.slug == tenant_slug,
            Tenant.is_active.is_(True),
        )
    )

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if tenant is None:
        raise unauthorized

    email = form_data.username.strip().lower()

    user = db.scalar(
        select(UserAccount).where(
            UserAccount.email == email,
            UserAccount.tenant_id == tenant.id,
        )
    )

    if user is None or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise unauthorized

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=str(user.id),
        tenant_id=tenant.id,
    )

    return TokenResponse(
        access_token=token,
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
    )


@router.get("/me")
def read_current_user(
    current_user: UserAccount = Depends(get_current_user),
) -> dict:
    """Return the identity of the currently authenticated user."""

    return {
        "id": current_user.id,
        "tenant_id": current_user.tenant_id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }


@router.get("/admin-check")
def admin_check(
    current_user: UserAccount = Depends(require_admin),
) -> dict:
    """Test administrator-only authorization."""

    return {
        "message": "Administrator access granted",
        "email": current_user.email,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
    }
