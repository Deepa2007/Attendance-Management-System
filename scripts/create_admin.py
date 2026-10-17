from getpass import getpass
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.tenant import Tenant
from app.models.user_account import UserAccount


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def main() -> None:
    tenant_name = input("Tenant name: ").strip()
    if len(tenant_name) < 2:
        print("Please enter a tenant name with at least 2 characters.")
        return

    tenant_slug = input("Tenant slug (lowercase, hyphens allowed): ").strip().lower()
    if not SLUG_PATTERN.fullmatch(tenant_slug):
        print("Slug must be lowercase letters, numbers, and hyphens.")
        return

    email = input("Administrator email: ").strip().lower()
    if not email or "@" not in email:
        print("Please enter a valid email address.")
        return

    password = getpass("Administrator password (hidden): ")
    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    confirmation = getpass("Confirm password (hidden): ")
    if password != confirmation:
        print("Passwords do not match.")
        return

    db = SessionLocal()

    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
        if tenant is None:
            tenant = Tenant(
                name=tenant_name,
                slug=tenant_slug,
                is_active=True,
            )
            db.add(tenant)
            db.flush()
        elif tenant.name != tenant_name:
            print(
                "A tenant with this slug already exists under a different name. "
                "No changes were made."
            )
            return

        existing_user = db.scalar(
            select(UserAccount).where(
                UserAccount.email == email,
                UserAccount.tenant_id == tenant.id,
            )
        )
        if existing_user is not None:
            print(
                "An account with this email already exists for this tenant. "
                "No changes were made."
            )
            return

        admin = UserAccount(
            tenant_id=tenant.id,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        print("Administrator account created successfully.")
        print(f"Tenant slug: {tenant.slug}")
        print(f"Account email: {email}")
        print("Login with header X-Tenant-Slug set to the tenant slug.")

    except IntegrityError:
        db.rollback()
        print(
            "Account creation failed because of a database constraint. "
            "No account was created by this attempt."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
