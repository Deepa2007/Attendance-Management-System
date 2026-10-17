from dataclasses import dataclass
from datetime import date, timedelta

MINIMUM_QUALIFYING_DAYS = 3
MINIMUM_DAILY_SECONDS = 5 * 60 * 60
MINIMUM_WEEKLY_SECONDS = 15 * 60 * 60
MAXIMUM_DAILY_SECONDS = 8 * 60 * 60


@dataclass(frozen=True)
class WeeklyPolicyStatus:
    week_start: date
    week_end: date
    qualifying_days: int
    completed_seconds: int
    remaining_days: int
    meets_daily_requirement: bool
    meets_weekly_hours_requirement: bool
    is_compliant: bool
    can_still_meet_daily_requirement: bool
    can_still_meet_weekly_hours_requirement: bool
    compliance_is_impossible: bool
    is_behind_schedule: bool


def evaluate_weekly_policy(
    *,
    week_start: date,
    as_of_date: date,
    daily_seconds: dict[date, int],
) -> WeeklyPolicyStatus:
    """
    Evaluate weekly attendance using completed daily seconds.

    week_start must be a Monday.
    daily_seconds maps local calendar dates to completed seconds.
    Future dates are ignored when calculating completed attendance.
    """

    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    week_end = week_start + timedelta(days=6)

    if as_of_date < week_start:
        raise ValueError("as_of_date cannot be before week_start")

    if as_of_date > week_end:
        as_of_date = week_end

    completed_dates = [
        week_start + timedelta(days=offset)
        for offset in range((as_of_date - week_start).days + 1)
    ]

    completed_seconds = sum(min(
        max(0, daily_seconds.get(day, 0)),
        MAXIMUM_DAILY_SECONDS,
        )
        for day in completed_dates
    )

    qualifying_days = sum(
        1
        for day in completed_dates
        if max(0, daily_seconds.get(day, 0))
        >= MINIMUM_DAILY_SECONDS
    )

    remaining_days = (week_end - as_of_date).days

    meets_daily_requirement = (
        qualifying_days >= MINIMUM_QUALIFYING_DAYS
    )
    meets_weekly_hours_requirement = (
        completed_seconds >= MINIMUM_WEEKLY_SECONDS
    )

    can_still_meet_daily_requirement = (
        qualifying_days + remaining_days
        >= MINIMUM_QUALIFYING_DAYS
    )

    can_still_meet_weekly_hours_requirement = (
        completed_seconds + remaining_days *  MAXIMUM_DAILY_SECONDS
        >= MINIMUM_WEEKLY_SECONDS
    )

    compliance_is_impossible = (
        not can_still_meet_daily_requirement
        or not can_still_meet_weekly_hours_requirement
    )

    # Wednesday and Friday are progress checkpoints.
    # At these checkpoints, being behind means that the employee
    # has not yet achieved both requirements.
    is_checkpoint = as_of_date.weekday() in (2, 4)

    is_behind_schedule = (
        is_checkpoint
        and not compliance_is_impossible
        and (
            not meets_daily_requirement
            or not meets_weekly_hours_requirement
        )
    )

    is_compliant = (
        meets_daily_requirement
        and meets_weekly_hours_requirement
    )

    return WeeklyPolicyStatus(
        week_start=week_start,
        week_end=week_end,
        qualifying_days=qualifying_days,
        completed_seconds=completed_seconds,
        remaining_days=remaining_days,
        meets_daily_requirement=meets_daily_requirement,
        meets_weekly_hours_requirement=(
            meets_weekly_hours_requirement
        ),
        is_compliant=is_compliant,
        can_still_meet_daily_requirement=(
            can_still_meet_daily_requirement
        ),
        can_still_meet_weekly_hours_requirement=(
            can_still_meet_weekly_hours_requirement
        ),
        compliance_is_impossible=compliance_is_impossible,
        is_behind_schedule=is_behind_schedule,
    )
