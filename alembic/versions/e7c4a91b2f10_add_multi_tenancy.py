"""add multi tenancy

Revision ID: e7c4a91b2f10
Revises: 6c73cb2dc1ac
Create Date: 2026-10-17 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7c4a91b2f10"
down_revision: Union[str, Sequence[str], None] = "6c73cb2dc1ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=False)
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    tenants = sa.table(
        "tenants",
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.execute(
        tenants.insert().values(
            name="Default Company",
            slug="default",
            is_active=True,
        )
    )

    op.add_column("employees", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.add_column("user_accounts", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.add_column(
        "attendance_sessions",
        sa.Column("tenant_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "attendance_notifications",
        sa.Column("tenant_id", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE employees
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE user_accounts
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE attendance_sessions AS sessions
        SET tenant_id = employees.tenant_id
        FROM employees
        WHERE sessions.employee_id = employees.id
          AND sessions.tenant_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE attendance_notifications AS notifications
        SET tenant_id = employees.tenant_id
        FROM employees
        WHERE notifications.employee_id = employees.id
          AND notifications.tenant_id IS NULL
        """
    )

    op.alter_column("employees", "tenant_id", nullable=False)
    op.alter_column("user_accounts", "tenant_id", nullable=False)
    op.alter_column("attendance_sessions", "tenant_id", nullable=False)
    op.alter_column("attendance_notifications", "tenant_id", nullable=False)

    op.create_foreign_key(
        "fk_employees_tenant_id",
        "employees",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_user_accounts_tenant_id",
        "user_accounts",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_attendance_sessions_tenant_id",
        "attendance_sessions",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_attendance_notifications_tenant_id",
        "attendance_notifications",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_index(op.f("ix_employees_email"), table_name="employees")
    op.create_index(op.f("ix_employees_email"), "employees", ["email"], unique=False)
    op.create_index("ix_employees_tenant_id", "employees", ["tenant_id"], unique=False)
    op.create_unique_constraint(
        "uq_employees_tenant_email",
        "employees",
        ["tenant_id", "email"],
    )

    op.drop_index(op.f("ix_user_accounts_email"), table_name="user_accounts")
    op.create_index(
        op.f("ix_user_accounts_email"),
        "user_accounts",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_user_accounts_tenant_id",
        "user_accounts",
        ["tenant_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_user_accounts_tenant_email",
        "user_accounts",
        ["tenant_id", "email"],
    )

    op.create_index(
        "ix_attendance_sessions_tenant_id",
        "attendance_sessions",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_notifications_tenant_id",
        "attendance_notifications",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attendance_notifications_tenant_id",
        table_name="attendance_notifications",
    )
    op.drop_index(
        "ix_attendance_sessions_tenant_id",
        table_name="attendance_sessions",
    )

    op.drop_constraint(
        "uq_user_accounts_tenant_email",
        "user_accounts",
        type_="unique",
    )
    op.drop_index("ix_user_accounts_tenant_id", table_name="user_accounts")
    op.drop_index(op.f("ix_user_accounts_email"), table_name="user_accounts")
    op.create_index(
        op.f("ix_user_accounts_email"),
        "user_accounts",
        ["email"],
        unique=True,
    )

    op.drop_constraint("uq_employees_tenant_email", "employees", type_="unique")
    op.drop_index("ix_employees_tenant_id", table_name="employees")
    op.drop_index(op.f("ix_employees_email"), table_name="employees")
    op.create_index(op.f("ix_employees_email"), "employees", ["email"], unique=True)

    op.drop_constraint(
        "fk_attendance_notifications_tenant_id",
        "attendance_notifications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_attendance_sessions_tenant_id",
        "attendance_sessions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_user_accounts_tenant_id",
        "user_accounts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_employees_tenant_id",
        "employees",
        type_="foreignkey",
    )

    op.drop_column("attendance_notifications", "tenant_id")
    op.drop_column("attendance_sessions", "tenant_id")
    op.drop_column("user_accounts", "tenant_id")
    op.drop_column("employees", "tenant_id")

    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_id"), table_name="tenants")
    op.drop_table("tenants")
