"""ORM ↔ engine glue. Thin translation layer — no business logic beyond data conversion.

Views call run_generation() to produce a Timetable (DRAFT) from an AcademicSession.
validate_move() is used by Phase 3 live clash validation.
"""
from django.utils import timezone

from core.models import AcademicSession, Period, Day
from catalog.models import Venue
from .models import Timetable, TimetableEntry
from .engine.types import SessionVar, Placement, ScheduledSession, GenerationResult
from .engine.solver import generate as engine_generate


def run_generation(
    session: AcademicSession,
    user,
    greedy_only: bool = False,
) -> tuple[Timetable, GenerationResult]:
    """Generate a timetable for *session*. Replaces any existing DRAFT cleanly (FR-B4).

    Raises ValueError if no Periods are configured.
    """
    periods = list(Period.objects.order_by("index"))
    if not periods:
        raise ValueError(
            "No periods configured. Run `python manage.py seed` or add periods in Time Config."
        )

    periods_per_day = len(periods)
    periods_by_index = {p.index: p for p in periods}
    days = [day_val for day_val, _ in Day.choices]
    venue_dicts = _build_venue_dicts()

    session_vars, no_lecturer_courses = _build_session_vars(session)

    # Core solver call — pure Python, no Django imports inside
    result = engine_generate(session_vars, days, periods_per_day, venue_dicts, greedy_only=greedy_only)

    # Courses with no lecturer assigned → add as unscheduled with explanation
    for course in no_lecturer_courses:
        for _ in range(course.weekly_sessions):
            result.unscheduled.append({
                "session": _SimpleSession(course.code),
                "reason": f"No lecturer assigned to {course.code}",
            })

    # Normalise unscheduled to plain dicts for JSON storage
    unscheduled_data = [
        {
            "course_code": _course_code(u["session"]),
            "reason": u["reason"],
        }
        for u in result.unscheduled
    ]

    # Find or create the DRAFT timetable for this session
    draft = Timetable.objects.filter(
        academic_session=session, status=Timetable.Status.DRAFT
    ).first()

    if draft is None:
        draft = Timetable(
            academic_session=session,
            status=Timetable.Status.DRAFT,
        )

    draft.name = f"{session} — Draft"
    draft.created_by = user
    draft.soft_score = result.soft_score
    draft.generation_time_ms = result.metrics.get("generation_time_ms", 0)
    draft.generated_at = timezone.now()
    draft.metrics = {**result.metrics, "unscheduled": unscheduled_data}
    draft.save()

    _persist_entries(draft, result, periods_by_index)
    return draft, result


def validate_move(
    entry: TimetableEntry,
    new_day: str,
    new_period_index: int,
    new_venue_id: int,
) -> str | None:
    """Check whether moving *entry* to a new slot violates any hard constraint.

    Returns a human-readable reason string on failure, None if the move is valid.
    Used by Phase 3 live clash validation endpoints.
    """
    from .engine.constraints import first_failure_reason

    period = Period.objects.get(index=new_period_index)
    venue = Venue.objects.get(pk=new_venue_id)
    periods_per_day = Period.objects.count()

    # All other entries in this timetable become the "current schedule"
    other_entries = (
        entry.timetable.entries
        .exclude(pk=entry.pk)
        .select_related("start_period", "venue", "lecturer", "course")
    )

    unavailable = frozenset(
        (u.day, u.period.index)
        for u in entry.lecturer.unavailabilities.all()
    )

    session_var = SessionVar(
        id=entry.pk,
        course_id=entry.course_id,
        course_code=entry.course.code,
        lecturer_id=entry.lecturer_id,
        required_venue_type=entry.venue.venue_type,
        class_size=entry.course.class_size,
        session_length=entry.length,
        unavailable=unavailable,
    )

    placement = Placement(
        day=new_day,
        start_period=new_period_index,
        venue_id=venue.pk,
        venue_capacity=venue.capacity,
        venue_type=venue.venue_type,
    )

    schedule = [_orm_entry_to_scheduled(e) for e in other_entries]
    return first_failure_reason(session_var, placement, schedule, periods_per_day)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_session_vars(
    session: AcademicSession,
) -> tuple[list[SessionVar], list]:
    """Convert ORM courses → engine SessionVar list.

    Also returns courses with no lecturer assigned (cannot be scheduled).
    """
    from catalog.models import Course

    courses = Course.objects.filter(academic_session=session).prefetch_related(
        "course_lecturers__lecturer__unavailabilities__period"
    )

    session_vars: list[SessionVar] = []
    no_lecturer: list = []
    var_id = 0

    for course in courses:
        first_cl = course.course_lecturers.first()
        if not first_cl:
            no_lecturer.append(course)
            continue

        lecturer = first_cl.lecturer
        unavailable = frozenset(
            (u.day, u.period.index) for u in lecturer.unavailabilities.all()
        )

        for _ in range(course.weekly_sessions):
            var_id += 1
            session_vars.append(
                SessionVar(
                    id=var_id,
                    course_id=course.pk,
                    course_code=course.code,
                    lecturer_id=lecturer.pk,
                    required_venue_type=course.required_venue_type,
                    class_size=course.class_size,
                    session_length=course.session_length,
                    unavailable=unavailable,
                )
            )

    return session_vars, no_lecturer


def _build_venue_dicts() -> list[dict]:
    return [
        {"id": v.pk, "capacity": v.capacity, "venue_type": v.venue_type}
        for v in Venue.objects.all()
    ]


def _persist_entries(
    timetable: Timetable,
    result: GenerationResult,
    periods_by_index: dict,
) -> None:
    """Delete all existing entries and bulk-create the new set (idempotent re-generation)."""
    timetable.entries.all().delete()
    TimetableEntry.objects.bulk_create([
        TimetableEntry(
            timetable=timetable,
            course_id=s.session.course_id,
            lecturer_id=s.session.lecturer_id,
            venue_id=s.placement.venue_id,
            day=s.placement.day,
            start_period=periods_by_index[s.placement.start_period],
            length=s.session.session_length,
        )
        for s in result.entries
    ])


def _orm_entry_to_scheduled(entry: TimetableEntry) -> ScheduledSession:
    unavailable = frozenset(
        (u.day, u.period.index) for u in entry.lecturer.unavailabilities.all()
    )
    sv = SessionVar(
        id=entry.pk,
        course_id=entry.course_id,
        course_code=entry.course.code,
        lecturer_id=entry.lecturer_id,
        required_venue_type=entry.venue.venue_type,
        class_size=entry.course.class_size,
        session_length=entry.length,
        unavailable=unavailable,
    )
    p = Placement(
        day=entry.day,
        start_period=entry.start_period.index,
        venue_id=entry.venue_id,
        venue_capacity=entry.venue.capacity,
        venue_type=entry.venue.venue_type,
    )
    return ScheduledSession(session=sv, placement=p)


class _SimpleSession:
    """Minimal stand-in for SessionVar when building unscheduled entries for courses with no lecturer."""
    def __init__(self, code: str):
        self.course_code = code


def _course_code(session_obj) -> str:
    if hasattr(session_obj, "course_code"):
        return session_obj.course_code
    if isinstance(session_obj, dict):
        return session_obj.get("course_code", "?")
    return str(session_obj)
