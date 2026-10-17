from datetime import date,datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AttendanceNotification(Base):
    __tablename__ = "attendance_notifications"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "week_start",
            "notification_type",
            "milestone_key",
            name="uq_attendance_notification_dedup",
        ),
        CheckConstraint(
            "notification_type IN "
            "('progress_reminder', 'impossible_warning', "
            "'final_weekly_warning')",
            name="ck_attendance_notification_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'failed')",
            name="ck_attendance_notification_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_attendance_notification_attempt_count",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        nullable=False,
    )

    week_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    milestone_key: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="none",
    )

    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
