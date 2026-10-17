
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.user_account import UserAccount

def main() -> None:
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
        existing_user = db.scalar(
            select(UserAccount).where(UserAccount.email == email)
        )

        if existing_user is not None:
            print(
                "An account with this email already exists. "
                "No changes were made."
            )
            return

        admin = UserAccount(
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print("Administrator account created successfully.")
        print(f"Account email: {email}")

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
