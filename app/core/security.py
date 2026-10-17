
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Convert a plain-text password into a secure password hash."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Check whether a password matches its stored hash."""
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str, tenant_id: int) -> str:
    """Create a signed JWT with an expiration time and tenant claim."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "tid": tenant_id,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict | None:
    """Validate a JWT and return its claims, or None if invalid."""
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "tid", "iat", "exp"]},
        )
    except InvalidTokenError:
        return None
