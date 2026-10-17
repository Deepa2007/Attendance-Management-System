from datetime import date, timedelta

from app.services.attendance_policy import evaluate_weekly_policy


WEEK_START = date(2026, 10, 12)  # Monday


def test_wednesday_employee_behind_but_can_still_comply():
    result = evaluate_weekly_policy(
        week_start=WEEK_START,
        as_of_date=date(2026, 10, 14),  # Wednesday
        daily_seconds={
            date(2026, 10, 12): 5 * 3600,
        },
    )

    assert result.qualifying_days == 1
    assert result.is_behind_schedule is True
    assert result.compliance_is_impossible is False


def test_friday_employee_behind_but_can_still_comply():
    result = evaluate_weekly_policy(
        week_start=WEEK_START,
        as_of_date=date(2026, 10, 16),  # Friday
        daily_seconds={
            date(2026, 10, 12): 5 * 3600,
            date(2026, 10, 13): 5 * 3600,
            date(2026, 10, 14): 2 * 3600,
        },
    )

    assert result.qualifying_days == 2
    assert result.completed_seconds == 12 * 3600
    assert result.is_behind_schedule is True
    assert result.compliance_is_impossible is False


def test_daily_requirement_becomes_impossible_on_friday():
    result = evaluate_weekly_policy(
        week_start=WEEK_START,
        as_of_date=date(2026, 10, 16),  # Friday
        daily_seconds={
            date(2026, 10, 12): 5 * 3600,
            date(2026, 10, 13): 5 * 3600,
        },
    )

    # Only Saturday and Sunday remain, so a third qualifying day
    # is still possible. This must not trigger an impossible warning.
    assert result.can_still_meet_daily_requirement is True
    assert result.compliance_is_impossible is False


def test_daily_requirement_impossible_after_sunday():
    result = evaluate_weekly_policy(
        week_start=WEEK_START,
        as_of_date=date(2026, 10, 18),  # Sunday
        daily_seconds={
            date(2026, 10, 12): 5 * 3600,
            date(2026, 10, 13): 5 * 3600,
        },
    )

    assert result.can_still_meet_daily_requirement is False
    assert result.compliance_is_impossible is True


def test_fifteen_hours_and_three_qualifying_days_is_compliant():
    result = evaluate_weekly_policy(
        week_start=WEEK_START,
        as_of_date=date(2026, 10, 16),  # Friday
        daily_seconds={
            date(2026, 10, 12): 5 * 3600,
            date(2026, 10, 13): 5 * 3600,
            date(2026, 10, 14): 5 * 3600,
        },
    )

    assert result.qualifying_days == 3
    assert result.completed_seconds == 15 * 3600
    assert result.is_compliant is True
    assert result.compliance_is_impossible is False


def test_week_start_must_be_monday():
    try:
        evaluate_weekly_policy(
            week_start=date(2026, 10, 13),  # Tuesday
            as_of_date=date(2026, 10, 14),
            daily_seconds={},
        )
    except ValueError as exc:
        assert "Monday" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-Monday week start")
