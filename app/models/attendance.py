
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
    )

    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    checked_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "checked_out_at IS NULL OR "
            "checked_out_at >= checked_in_at",
            name="ck_attendance_checkout_after_checkin",
        ),
        Index(
            "ix_attendance_employee_checkin",
            "employee_id",
            "checked_in_at",
        ),
        Index(
            "uq_attendance_one_active_session_per_employee",
            "employee_id",
            unique=True,
            postgresql_where=checked_out_at.is_(None),
        ),
    )
