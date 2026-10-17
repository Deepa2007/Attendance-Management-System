
from datetime import date

from app.services.attendance_policy import WeeklyPolicyStatus
from app.services.notification_decisions import decide_notifications


def make_status(**overrides):
    values = {
        "week_start": date(2026, 10, 12),
        "week_end": date(2026, 10, 18),
        "qualifying_days": 1,
        "completed_seconds": 6 * 60 * 60,
        "remaining_days": 3,
        "meets_daily_requirement": False,
        "meets_weekly_hours_requirement": False,
        "is_compliant": False,
        "can_still_meet_daily_requirement": True,
        "can_still_meet_weekly_hours_requirement": True,
        "compliance_is_impossible": False,
        "is_behind_schedule": True,
    }
    values.update(overrides)
    return WeeklyPolicyStatus(**values)


def test_behind_schedule_creates_progress_reminder():
    decisions = decide_notifications(
        policy_status=make_status(),
        as_of_date=date(2026, 10, 14),
        is_final_evaluation_due=False,
    )

    assert len(decisions) == 1
    assert decisions[0].notification_type == "progress_reminder"


def test_impossible_three_day_requirement_creates_warning():
    decisions = decide_notifications(
        policy_status=make_status(
            can_still_meet_daily_requirement=False,
            compliance_is_impossible=True,
            is_behind_schedule=False,
        ),
        as_of_date=date(2026, 10, 18),
        is_final_evaluation_due=False,
    )

    assert len(decisions) == 1
    assert decisions[0].notification_type == "impossible_warning"


def test_compliant_week_does_not_get_final_warning():
    decisions = decide_notifications(
        policy_status=make_status(
            qualifying_days=3,
            completed_seconds=15 * 60 * 60,
            meets_daily_requirement=True,
            meets_weekly_hours_requirement=True,
            is_compliant=True,
            is_behind_schedule=False,
        ),
        as_of_date=date(2026, 10, 18),
        is_final_evaluation_due=True,
    )

    assert decisions == []


def test_noncompliant_week_gets_final_warning_after_grace_period():
    decisions = decide_notifications(
        policy_status=make_status(),
        as_of_date=date(2026, 10, 18),
        is_final_evaluation_due=True,
    )

    assert len(decisions) == 1
    assert decisions[0].notification_type == "final_weekly_warning"


def test_no_reminder_when_not_behind_schedule():
    decisions = decide_notifications(
        policy_status=make_status(is_behind_schedule=False),
        as_of_date=date(2026, 10, 14),
        is_final_evaluation_due=False,
    )

    assert decisions == []
