from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.tenant import Tenant
from app.models.user_account import UserAccount


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserAccount:
    """Validate the JWT and retrieve the active user in that tenant."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)

    if payload is None:
        raise unauthorized

    subject = payload.get("sub")
    tenant_claim = payload.get("tid")

    if not isinstance(subject, str) or not subject.isdigit():
        raise unauthorized

    if not isinstance(tenant_claim, int):
        raise unauthorized

    user = db.scalar(
        select(UserAccount).where(
            UserAccount.id == int(subject),
            UserAccount.tenant_id == tenant_claim,
        )
    )

    if user is None or not user.is_active:
        raise unauthorized

    tenant = db.get(Tenant, user.tenant_id)
    if tenant is None or not tenant.is_active:
        raise unauthorized

    return user


def require_admin(
    current_user: UserAccount = Depends(get_current_user),
) -> UserAccount:
    """Allow only active administrator accounts for the current tenant."""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return current_user
