"""Dataclasses shared by the entire engine. No Django imports allowed here."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SessionVar:
    """One scheduling variable: a single weekly session of a course."""
    id: int                   # unique id for this variable
    course_id: int
    course_code: str
    lecturer_id: int
    required_venue_type: str  # "LECTURE_HALL" | "LAB" | "SEMINAR"
    class_size: int
    session_length: int       # consecutive periods needed
    unavailable: frozenset    # frozenset of (day, period_index) when lecturer unavailable


@dataclass(frozen=True)
class Placement:
    day: str           # e.g. "MON"
    start_period: int  # 1-indexed period number
    venue_id: int
    venue_capacity: int
    venue_type: str


@dataclass
class ScheduledSession:
    session: SessionVar
    placement: Placement


@dataclass
class GenerationResult:
    entries: list[ScheduledSession] = field(default_factory=list)
    unscheduled: list[dict] = field(default_factory=list)  # [{session, reason}]
    hard_violations: int = 0   # MUST be 0 for any valid published solution
    soft_score: int = 0        # lower is better
    metrics: dict = field(default_factory=dict)
