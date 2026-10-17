
from alembic import context

from app.db.base import Base
from app.db.database import DATABASE_URL, engine

from app.models.tenant import Tenant
from app.models.employee import Employee
from app.models.attendance import AttendanceSession
from app.models.user_account import UserAccount
from app.models.attendance_notification import AttendanceNotification

# Import models here as we create them so Alembic
# can discover their tables.
# from app.models.employee import Employee
# from app.models.attendance import AttendanceSession

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without opening a database connection."""
    context.configure(
        url=DATABASE_URL.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
