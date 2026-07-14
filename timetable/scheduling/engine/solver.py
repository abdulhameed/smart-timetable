"""Constraint-based timetable solver.

Algorithm: greedy assignment with CSP heuristics + bounded backtracking.
  - MRV (Minimum Remaining Values): schedule most-constrained sessions first.
  - Degree heuristic tie-break: prefer sessions with busiest lecturers.
  - LCV-style placement selection: among hard-valid candidates, pick lowest soft score.
  - Bounded backtracking: MAX_ATTEMPTS prevents exponential blow-up on infeasible inputs.

No Django imports. Call via scheduling/services.py.
"""
import time
from .types import SessionVar, Placement, ScheduledSession, GenerationResult
from .constraints import hard_valid_placements, soft_score, first_failure_reason

MAX_ATTEMPTS = 500


def generate(
    sessions: list[SessionVar],
    days: list[str],
    periods_per_day: int,
    venues: list[dict],  # [{"id", "capacity", "venue_type"}]
    greedy_only: bool = False,
) -> GenerationResult:
    """Entry point. Returns a GenerationResult.

    Set greedy_only=True to disable backtracking (for evaluation comparison).
    """
    start = time.perf_counter()

    all_placements = _build_candidate_pool(days, periods_per_day, venues)
    schedule: list[ScheduledSession] = []
    unscheduled: list[dict] = []

    # MRV ordering: sort sessions by domain size ascending, degree (lecturer load) descending
    ordered = _mrv_order(sessions, all_placements, periods_per_day)

    if greedy_only:
        _greedy_assign(ordered, all_placements, schedule, unscheduled, periods_per_day)
    else:
        _backtrack(ordered, 0, all_placements, schedule, unscheduled, periods_per_day, [0])

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    metrics = _compute_metrics(schedule, unscheduled, days, periods_per_day, venues, elapsed_ms)

    return GenerationResult(
        entries=schedule,
        unscheduled=unscheduled,
        hard_violations=0,  # hard_valid_placements guarantees this
        soft_score=sum(e.get("soft_penalty", 0) for e in metrics.get("_placement_scores", [])),
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Ordering heuristics
# ---------------------------------------------------------------------------

def _mrv_order(
    sessions: list[SessionVar],
    all_placements: list[Placement],
    periods_per_day: int,
) -> list[SessionVar]:
    """Sort by domain size ascending (MRV), then lecturer_id frequency descending (degree)."""
    lecturer_counts: dict[int, int] = {}
    for s in sessions:
        lecturer_counts[s.lecturer_id] = lecturer_counts.get(s.lecturer_id, 0) + 1

    def key(s: SessionVar):
        # domain size: placements compatible with venue type + H4/H5/H6 (ignoring schedule state)
        domain = sum(
            1 for p in all_placements
            if p.venue_type == s.required_venue_type
            and p.venue_capacity >= s.class_size
            and p.start_period + s.session_length - 1 <= periods_per_day
        )
        load = lecturer_counts.get(s.lecturer_id, 0)
        return (domain, -load)

    return sorted(sessions, key=key)


# ---------------------------------------------------------------------------
# Greedy assign (no backtracking)
# ---------------------------------------------------------------------------

def _greedy_assign(
    sessions: list[SessionVar],
    all_placements: list[Placement],
    schedule: list[ScheduledSession],
    unscheduled: list[dict],
    periods_per_day: int,
) -> None:
    dept_day_counts: dict[str, int] = {}

    for session in sessions:
        candidates = [
            p for p in all_placements if p.venue_type == session.required_venue_type
        ]
        valid = hard_valid_placements(session, candidates, schedule, periods_per_day)

        if not valid:
            reason = _unschedulable_reason(session, candidates, schedule, periods_per_day)
            unscheduled.append({"session": session, "reason": reason})
            continue

        best = min(valid, key=lambda p: soft_score(session, p, schedule, dept_day_counts, periods_per_day))
        schedule.append(ScheduledSession(session=session, placement=best))
        dept_day_counts[best.day] = dept_day_counts.get(best.day, 0) + 1


# ---------------------------------------------------------------------------
# Backtracking solver
# ---------------------------------------------------------------------------

def _backtrack(
    sessions: list[SessionVar],
    index: int,
    all_placements: list[Placement],
    schedule: list[ScheduledSession],
    unscheduled: list[dict],
    periods_per_day: int,
    attempts: list[int],  # mutable counter wrapped in list
) -> bool:
    if index == len(sessions):
        return True

    if attempts[0] > MAX_ATTEMPTS:
        # Exceeded attempt budget — greedily assign the rest
        _greedy_assign(sessions[index:], all_placements, schedule, unscheduled, periods_per_day)
        return True

    session = sessions[index]
    candidates = [p for p in all_placements if p.venue_type == session.required_venue_type]
    valid = hard_valid_placements(session, candidates, schedule, periods_per_day)

    if not valid:
        reason = _unschedulable_reason(session, candidates, schedule, periods_per_day)
        unscheduled.append({"session": session, "reason": reason})
        attempts[0] += 1
        return _backtrack(sessions, index + 1, all_placements, schedule, unscheduled, periods_per_day, attempts)

    dept_day_counts: dict[str, int] = {}
    for e in schedule:
        dept_day_counts[e.placement.day] = dept_day_counts.get(e.placement.day, 0) + 1

    sorted_valid = sorted(valid, key=lambda p: soft_score(session, p, schedule, dept_day_counts, periods_per_day))

    for placement in sorted_valid:
        schedule.append(ScheduledSession(session=session, placement=placement))
        attempts[0] += 1
        if _backtrack(sessions, index + 1, all_placements, schedule, unscheduled, periods_per_day, attempts):
            return True
        schedule.pop()

    # No candidate led to a complete solution — leave unscheduled and continue
    reason = _unschedulable_reason(session, candidates, schedule, periods_per_day)
    unscheduled.append({"session": session, "reason": reason})
    return _backtrack(sessions, index + 1, all_placements, schedule, unscheduled, periods_per_day, attempts)


# ---------------------------------------------------------------------------
# Candidate pool and metrics
# ---------------------------------------------------------------------------

def _build_candidate_pool(
    days: list[str],
    periods_per_day: int,
    venues: list[dict],
) -> list[Placement]:
    placements = []
    for day in days:
        for period in range(1, periods_per_day + 1):
            for venue in venues:
                placements.append(Placement(
                    day=day,
                    start_period=period,
                    venue_id=venue["id"],
                    venue_capacity=venue["capacity"],
                    venue_type=venue["venue_type"],
                ))
    return placements


def _unschedulable_reason(
    session: SessionVar,
    candidates: list[Placement],
    schedule: list[ScheduledSession],
    periods_per_day: int,
) -> str:
    """Return the most informative reason why a session cannot be placed."""
    if not candidates:
        return f"No venues of type '{session.required_venue_type}' exist"
    capacity_ok = [p for p in candidates if p.venue_capacity >= session.class_size]
    if not capacity_ok:
        max_cap = max(p.venue_capacity for p in candidates)
        return f"No venue of type '{session.required_venue_type}' has capacity >= {session.class_size} (max: {max_cap})"
    return "All valid slots are occupied (lecturer/venue/course clashes)"


def _compute_metrics(
    schedule: list[ScheduledSession],
    unscheduled: list[dict],
    days: list[str],
    periods_per_day: int,
    venues: list[dict],
    elapsed_ms: int,
) -> dict:
    total_slots = len(days) * periods_per_day * len(venues)
    used_slots = len(schedule)
    utilisation = round(used_slots / total_slots * 100, 1) if total_slots else 0

    per_day: dict[str, int] = {d: 0 for d in days}
    for e in schedule:
        per_day[e.placement.day] = per_day.get(e.placement.day, 0) + 1

    # Back-to-back count: sessions for same lecturer on same day with no gap
    back_to_back = 0
    lecturer_days: dict[tuple, list] = {}
    for e in schedule:
        key = (e.session.lecturer_id, e.placement.day)
        lecturer_days.setdefault(key, []).append((e.placement.start_period, e.session.session_length))
    for segs in lecturer_days.values():
        segs.sort()
        for i in range(len(segs) - 1):
            end = segs[i][0] + segs[i][1]
            if end == segs[i + 1][0]:
                back_to_back += 1

    return {
        "generation_time_ms": elapsed_ms,
        "venue_utilisation_pct": utilisation,
        "per_day_counts": per_day,
        "back_to_back_count": back_to_back,
        "scheduled_count": len(schedule),
        "unscheduled_count": len(unscheduled),
    }
