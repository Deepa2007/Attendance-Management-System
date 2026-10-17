
from dataclasses import dataclass
from datetime import date, datetime

from app.services.attendance_policy import WeeklyPolicyStatus


@dataclass(frozen=True)
class NotificationDecision:
    notification_type: str
    milestone_key: str

def decide_notifications(
    *,
    policy_status: WeeklyPolicyStatus,
    as_of_date: date,
    is_final_evaluation_due: bool,
) -> list[NotificationDecision]:
    decisions = []

    if is_final_evaluation_due:
        if not policy_status.is_compliant:
            decisions.append(
                NotificationDecision(
                    notification_type="final_weekly_warning",
                    milestone_key="final_evaluation",
                )
            )
        return decisions

    if (
        not policy_status.can_still_meet_daily_requirement
        or not policy_status.can_still_meet_weekly_hours_requirement
    ):
        milestone_key = (
            "three_day_requirement"
            if not policy_status.can_still_meet_daily_requirement
            else "weekly_hours_requirement"
        )

        decisions.append(
            NotificationDecision(
                notification_type="impossible_warning",
                milestone_key=milestone_key,
            )
        )
        return decisions

    if policy_status.is_behind_schedule:
        decisions.append(
            NotificationDecision(
                notification_type="progress_reminder",
                milestone_key=f"progress_{as_of_date.isoformat()}",
            )
        )

    return decisions