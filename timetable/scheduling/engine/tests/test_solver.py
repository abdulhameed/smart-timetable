"""Solver-level tests: feasibility, infeasibility, determinism, greedy vs backtracking.

Framework-free — run with: pytest scheduling/engine/tests/ --noconftest
"""
import pytest
from ..types import SessionVar
from ..solver import generate
from ..constraints import soft_score, SOFT_WEIGHTS


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def make_session(
    id=1, course_id=1, course_code="CS101", lecturer_id=1,
    venue_type="LECTURE_HALL", class_size=30, session_length=1, unavailable=None,
):
    return SessionVar(
        id=id, course_id=course_id, course_code=course_code,
        lecturer_id=lecturer_id, required_venue_type=venue_type,
        class_size=class_size, session_length=session_length,
        unavailable=frozenset(unavailable or []),
    )


LH = "LECTURE_HALL"
LAB = "LAB"

DAYS_2 = ["MON", "TUE"]
DAYS_5 = ["MON", "TUE", "WED", "THU", "FRI"]


def venues_lh(n=2, capacity=100):
    return [{"id": i + 1, "capacity": capacity, "venue_type": LH} for i in range(n)]


# ---------------------------------------------------------------------------
# Feasible fixture — all sessions should schedule
# ---------------------------------------------------------------------------

def test_feasible_two_sessions_two_venues():
    sessions = [
        make_session(id=1, course_id=1, lecturer_id=1),
        make_session(id=2, course_id=2, lecturer_id=2),
    ]
    result = generate(sessions, ["MON"], 4, venues_lh(2))
    assert result.hard_violations == 0
    assert len(result.entries) == 2
    assert len(result.unscheduled) == 0


def test_feasible_many_sessions_spread_across_days():
    sessions = [make_session(id=i, course_id=i, lecturer_id=i) for i in range(1, 11)]
    result = generate(sessions, DAYS_5, 8, venues_lh(4))
    assert result.hard_violations == 0
    assert len(result.entries) == 10
    assert len(result.unscheduled) == 0


def test_feasible_multi_period_session():
    """A session_length=2 entry should fit within the working day."""
    sessions = [make_session(id=1, course_id=1, lecturer_id=1, session_length=2)]
    result = generate(sessions, ["MON"], 4, venues_lh(1))
    assert result.hard_violations == 0
    assert len(result.entries) == 1
    entry = result.entries[0]
    # Must not overflow: start_period + length - 1 <= periods_per_day
    assert entry.placement.start_period + entry.session.session_length - 1 <= 4


def test_feasible_no_lecturer_clash_in_result():
    """Two sessions for the same lecturer must land in different slots."""
    sessions = [
        make_session(id=1, course_id=1, lecturer_id=1),
        make_session(id=2, course_id=2, lecturer_id=1),   # same lecturer
    ]
    result = generate(sessions, ["MON"], 4, venues_lh(2))
    assert result.hard_violations == 0
    assert len(result.entries) == 2
    e1, e2 = result.entries[0].placement, result.entries[1].placement
    # Same day → must be different periods (no overlap)
    if e1.day == e2.day:
        assert not (e1.start_period == e2.start_period)


def test_feasible_respects_lecturer_unavailability():
    """Entries must never land in a lecturer's unavailable slots."""
    blocked = [("MON", 1), ("MON", 2), ("MON", 3)]
    sessions = [make_session(id=1, course_id=1, lecturer_id=1, unavailable=blocked)]
    result = generate(sessions, ["MON"], 4, venues_lh(1))
    assert result.hard_violations == 0
    if result.entries:
        p = result.entries[0].placement
        assert (p.day, p.start_period) not in blocked


# ---------------------------------------------------------------------------
# Infeasible fixture — system must return partial schedule, never invalid
# ---------------------------------------------------------------------------

def test_infeasible_returns_partial_never_invalid():
    """1 venue, 1 day, 1 period → only 1 of 3 courses can be placed."""
    sessions = [make_session(id=i, course_id=i, lecturer_id=i) for i in range(1, 4)]
    result = generate(sessions, ["MON"], 1, venues_lh(1))
    assert result.hard_violations == 0                        # NEVER violated
    assert len(result.entries) + len(result.unscheduled) == 3 # every session accounted for
    assert len(result.entries) <= 1                           # at most 1 fits


def test_infeasible_unscheduled_have_reasons():
    sessions = [make_session(id=i, course_id=i, lecturer_id=i) for i in range(1, 5)]
    result = generate(sessions, ["MON"], 1, venues_lh(1))
    for u in result.unscheduled:
        assert u["reason"], "Every unscheduled session must carry a reason"


def test_infeasible_capacity_constraint():
    """Session with class_size=200 cannot fit in capacity=50 venue → unscheduled."""
    sessions = [make_session(id=1, course_id=1, lecturer_id=1, class_size=200)]
    result = generate(sessions, DAYS_5, 8, venues_lh(4, capacity=50))
    assert result.hard_violations == 0
    assert len(result.entries) == 0
    assert len(result.unscheduled) == 1
    assert "capacity" in result.unscheduled[0]["reason"].lower()


def test_infeasible_fully_blocked_lecturer():
    """Lecturer unavailable every slot → session must be unscheduled."""
    all_blocked = [("MON", p) for p in range(1, 5)]
    sessions = [make_session(id=1, course_id=1, lecturer_id=1, unavailable=all_blocked)]
    result = generate(sessions, ["MON"], 4, venues_lh(2))
    assert result.hard_violations == 0
    assert len(result.entries) == 0
    assert len(result.unscheduled) == 1


# ---------------------------------------------------------------------------
# Determinism — same input → identical output
# ---------------------------------------------------------------------------

def test_determinism_same_input_same_output():
    sessions = [make_session(id=i, course_id=i, lecturer_id=i) for i in range(1, 8)]
    kwargs = dict(days=DAYS_5, periods_per_day=6, venues=venues_lh(3))
    result_a = generate(sessions, **kwargs)
    result_b = generate(sessions, **kwargs)
    placed_a = frozenset(
        (e.session.id, e.placement.day, e.placement.start_period, e.placement.venue_id)
        for e in result_a.entries
    )
    placed_b = frozenset(
        (e.session.id, e.placement.day, e.placement.start_period, e.placement.venue_id)
        for e in result_b.entries
    )
    assert placed_a == placed_b


# ---------------------------------------------------------------------------
# Greedy vs backtracking
# ---------------------------------------------------------------------------

def test_greedy_flag_does_not_produce_hard_violations():
    sessions = [make_session(id=i, course_id=i, lecturer_id=i) for i in range(1, 6)]
    result = generate(sessions, DAYS_2, 4, venues_lh(2), greedy_only=True)
    assert result.hard_violations == 0


def test_backtracking_schedules_at_least_as_many_as_greedy():
    """Backtracking should never schedule fewer sessions than greedy."""
    sessions = [make_session(id=i, course_id=i, lecturer_id=i) for i in range(1, 12)]
    kwargs = dict(days=DAYS_2, periods_per_day=4, venues=venues_lh(2))
    greedy = generate(sessions, **kwargs, greedy_only=True)
    bt = generate(sessions, **kwargs, greedy_only=False)
    assert len(bt.entries) >= len(greedy.entries)


# ---------------------------------------------------------------------------
# Soft-constraint scoring — S2 (day overload) and S3 (idle gap)
# ---------------------------------------------------------------------------

def test_s2_day_overload_penalised():
    """Placing sessions on an already-loaded day should cost more."""
    s = make_session(id=3, course_id=3, lecturer_id=3)

    from ..types import Placement, ScheduledSession

    def make_placed(id, period, day="MON"):
        sv = make_session(id=id, course_id=id, lecturer_id=id)
        p = Placement("MON", period, venue_id=id, venue_capacity=100, venue_type=LH)
        return ScheduledSession(session=sv, placement=p)

    # Busy Monday: 4 entries already there
    schedule = [make_placed(i, i) for i in range(10, 14)]
    busy_counts = {"MON": 4}
    empty_counts = {"TUE": 0}

    p_mon = Placement("MON", 5, venue_id=99, venue_capacity=100, venue_type=LH)
    p_tue = Placement("TUE", 1, venue_id=99, venue_capacity=100, venue_type=LH)

    score_overloaded = soft_score(s, p_mon, schedule, busy_counts, 8)
    score_empty = soft_score(s, p_tue, schedule, empty_counts, 8)
    assert score_overloaded >= score_empty


def test_s3_idle_gap_penalised():
    """A larger idle gap in a lecturer's day incurs a higher S3 penalty.

    We compare two non-back-to-back placements so S1 does not interfere:
    - existing at P1 (len 1), candidate at P4: idle gap = 4-2 = 2  → S3 += 1*(2-1) = 1
    - existing at P1 (len 1), candidate at P6: idle gap = 6-2 = 4  → S3 += 1*(4-1) = 3
    """
    from ..types import Placement, ScheduledSession

    lecturer_id = 5
    s = make_session(id=2, course_id=2, lecturer_id=lecturer_id)

    existing_session = make_session(id=1, course_id=1, lecturer_id=lecturer_id)
    existing_p = Placement("MON", 1, venue_id=1, venue_capacity=100, venue_type=LH)
    schedule = [ScheduledSession(session=existing_session, placement=existing_p)]

    # Both are non-adjacent (no S1 back-to-back), only S3 distinguishes them
    p_small_gap = Placement("MON", 4, venue_id=2, venue_capacity=100, venue_type=LH)
    p_large_gap = Placement("MON", 6, venue_id=2, venue_capacity=100, venue_type=LH)

    score_small = soft_score(s, p_small_gap, schedule, {}, 8)
    score_large = soft_score(s, p_large_gap, schedule, {}, 8)
    assert score_large > score_small
