"""Hard constraint predicates (H1–H6) and soft-constraint scoring (S1–S4).

Each hard constraint is an isolated predicate so tests and the viva can point
at exactly one function per rule. `hard_valid_placements` is the single
chokepoint — call nothing else to check hard validity.

No Django imports. Receives plain data structures only.
"""
from .types import SessionVar, Placement, ScheduledSession

# ---------------------------------------------------------------------------
# Soft-constraint weights (tunable)
# ---------------------------------------------------------------------------
SOFT_WEIGHTS = {
    "S1_back_to_back": 3,   # penalise back-to-back for same lecturer
    "S2_day_overload": 2,   # penalise day overloaded with same dept's courses
    "S3_idle_gap": 1,       # penalise large idle gap in lecturer's day
    "S4_late_period": 1,    # penalise very late periods
}

LATE_PERIOD_THRESHOLD = 7  # periods >= this index are "late"


# ---------------------------------------------------------------------------
# Hard constraints
# ---------------------------------------------------------------------------

def h1_lecturer_clash(
    session: SessionVar,
    placement: Placement,
    schedule: list[ScheduledSession],
) -> bool:
    """H1: A lecturer cannot teach two overlapping sessions."""
    for entry in schedule:
        if entry.session.lecturer_id != session.lecturer_id:
            continue
        if entry.placement.day != placement.day:
            continue
        if _overlaps(entry.placement.start_period, entry.session.session_length,
                     placement.start_period, session.session_length):
            return False
    return True


def h2_venue_clash(
    session: SessionVar,
    placement: Placement,
    schedule: list[ScheduledSession],
) -> bool:
    """H2: A venue cannot host two overlapping sessions."""
    for entry in schedule:
        if entry.placement.venue_id != placement.venue_id:
            continue
        if entry.placement.day != placement.day:
            continue
        if _overlaps(entry.placement.start_period, entry.session.session_length,
                     placement.start_period, session.session_length):
            return False
    return True


def h3_course_clash(
    session: SessionVar,
    placement: Placement,
    schedule: list[ScheduledSession],
) -> bool:
    """H3: The same course cannot be scheduled twice in the same time slot."""
    for entry in schedule:
        if entry.session.course_id != session.course_id:
            continue
        if entry.placement.day != placement.day:
            continue
        if _overlaps(entry.placement.start_period, entry.session.session_length,
                     placement.start_period, session.session_length):
            return False
    return True


def h4_venue_capacity(session: SessionVar, placement: Placement) -> bool:
    """H4: Venue capacity must be >= class size."""
    return placement.venue_capacity >= session.class_size


def h5_lecturer_availability(
    session: SessionVar,
    placement: Placement,
) -> bool:
    """H5: Session must lie entirely within the lecturer's availability."""
    for period_offset in range(session.session_length):
        period = placement.start_period + period_offset
        if (placement.day, period) in session.unavailable:
            return False
    return True


def h6_within_working_hours(
    session: SessionVar,
    placement: Placement,
    periods_per_day: int,
) -> bool:
    """H6: Session must not overflow past the last period of the day."""
    return placement.start_period + session.session_length - 1 <= periods_per_day


# ---------------------------------------------------------------------------
# Combined hard-validity check
# ---------------------------------------------------------------------------

def hard_valid_placements(
    session: SessionVar,
    candidates: list[Placement],
    schedule: list[ScheduledSession],
    periods_per_day: int,
) -> list[tuple[Placement, str | None]]:
    """Return (placement, None) for hard-valid candidates, or (placement, reason) for failures.

    Returns only valid placements. `reason` is None for valid ones;
    callers that need to report failures should check separately.
    """
    valid = []
    for p in candidates:
        if not h4_venue_capacity(session, p):
            continue
        if not h5_lecturer_availability(session, p):
            continue
        if not h6_within_working_hours(session, p, periods_per_day):
            continue
        if not h1_lecturer_clash(session, p, schedule):
            continue
        if not h2_venue_clash(session, p, schedule):
            continue
        if not h3_course_clash(session, p, schedule):
            continue
        valid.append(p)
    return valid


def first_failure_reason(
    session: SessionVar,
    placement: Placement,
    schedule: list[ScheduledSession],
    periods_per_day: int,
) -> str | None:
    """Return a human-readable reason why a placement is invalid, or None if valid."""
    if not h4_venue_capacity(session, placement):
        return f"Venue capacity {placement.venue_capacity} < class size {session.class_size}"
    if not h5_lecturer_availability(session, placement):
        return "Lecturer unavailable during required periods"
    if not h6_within_working_hours(session, placement, periods_per_day):
        return "Session would overflow past the last period of the day"
    if not h1_lecturer_clash(session, placement, schedule):
        return "Lecturer already teaching another session at this time"
    if not h2_venue_clash(session, placement, schedule):
        return "Venue already occupied at this time"
    if not h3_course_clash(session, placement, schedule):
        return "Course already scheduled at this time"
    return None


# ---------------------------------------------------------------------------
# Soft-constraint scoring
# ---------------------------------------------------------------------------

def soft_score(
    session: SessionVar,
    placement: Placement,
    schedule: list[ScheduledSession],
    dept_day_counts: dict,
    periods_per_day: int,
) -> int:
    """Return the weighted penalty for placing `session` at `placement`.

    Lower is better. Pure function — no side effects.
    """
    score = 0

    # S1: back-to-back for same lecturer
    for entry in schedule:
        if entry.session.lecturer_id != session.lecturer_id:
            continue
        if entry.placement.day != placement.day:
            continue
        gap = _gap(entry.placement.start_period, entry.session.session_length,
                   placement.start_period, session.session_length)
        if gap == 0:
            score += SOFT_WEIGHTS["S1_back_to_back"]

    # S2: day overload for same department
    day_key = (session.course_id, placement.day)  # approximate: per-course dept
    existing_count = dept_day_counts.get(placement.day, 0)
    if existing_count >= 3:
        score += SOFT_WEIGHTS["S2_day_overload"] * (existing_count - 2)

    # S3: idle gap in lecturer's day
    lecturer_periods = sorted(
        [
            (e.placement.start_period, e.session.session_length)
            for e in schedule
            if e.session.lecturer_id == session.lecturer_id
            and e.placement.day == placement.day
        ]
        + [(placement.start_period, session.session_length)]
    )
    if len(lecturer_periods) > 1:
        for i in range(len(lecturer_periods) - 1):
            end_of_prev = lecturer_periods[i][0] + lecturer_periods[i][1]
            start_of_next = lecturer_periods[i + 1][0]
            idle = start_of_next - end_of_prev
            if idle > 1:
                score += SOFT_WEIGHTS["S3_idle_gap"] * (idle - 1)

    # S4: late period
    session_end = placement.start_period + session.session_length - 1
    if session_end >= LATE_PERIOD_THRESHOLD:
        score += SOFT_WEIGHTS["S4_late_period"] * (session_end - LATE_PERIOD_THRESHOLD + 1)

    return score


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _overlaps(start_a: int, len_a: int, start_b: int, len_b: int) -> bool:
    """True if two intervals [start, start+len) overlap."""
    end_a = start_a + len_a
    end_b = start_b + len_b
    return start_a < end_b and start_b < end_a


def _gap(start_a: int, len_a: int, start_b: int, len_b: int) -> int:
    """Number of free periods between two intervals (0 = back-to-back)."""
    end_a = start_a + len_a
    end_b = start_b + len_b
    if start_b >= end_a:
        return start_b - end_a
    if start_a >= end_b:
        return start_a - end_b
    return 0  # overlapping — shouldn't happen after hard-validity check
