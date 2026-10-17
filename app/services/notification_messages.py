from app.services.email_provider import EmailMessage


def build_notification_email(
    *,
    recipient_email: str,
    notification_type: str,
    week_start,
    milestone_key: str,
) -> EmailMessage:
    """Build an attendance email without sending it."""

    if notification_type == "progress_reminder":
        subject = "Attendance policy progress reminder"
        body = (
            f"Hello,\n\n"
            f"This is a reminder to review your office attendance "
            f"for the week starting {week_start:%d %b %Y}.\n"
            f"Reminder milestone: {milestone_key}.\n\n"
            "Please check your attendance and ensure you meet the "
            "company's weekly attendance requirements.\n\n"
            "Regards,\nAttendance Management System"
        )

    elif notification_type == "impossible_warning":
        subject = "Attendance policy compliance warning"
        body = (
            f"Hello,\n\n"
            f"Your attendance for the week starting "
            f"{week_start:%d %b %Y} has reached a point where "
            "the required attendance target can no longer be met.\n"
            f"Requirement affected: {milestone_key}.\n\n"
            "Please contact your manager if you believe this "
            "assessment is incorrect.\n\n"
            "Regards,\nAttendance Management System"
        )

    elif notification_type == "final_weekly_warning":
        subject = "Final weekly attendance policy warning"
        body = (
            f"Hello,\n\n"
            f"The final attendance evaluation for the week starting "
            f"{week_start:%d %b %Y} indicates that the weekly "
            "attendance policy requirements were not met.\n\n"
            "Please review your attendance report and contact "
            "your manager if you believe this assessment is incorrect.\n\n"
            "Regards,\nAttendance Management System"
        )

    else:
        raise ValueError(
            f"Unsupported notification type: {notification_type}"
        )

    return EmailMessage(
        recipient=recipient_email,
        subject=subject,
        body=body,
    )
