"""Unit tests for hard constraints H1–H6 and soft-constraint scoring S1–S4.

Framework-free: run with plain `pytest scheduling/engine/tests/`.
"""
import pytest
from ..types import SessionVar, Placement, ScheduledSession
from ..constraints import (
    h1_lecturer_clash, h2_venue_clash, h3_course_clash,
    h4_venue_capacity, h5_lecturer_availability, h6_within_working_hours,
    soft_score, SOFT_WEIGHTS,
)

PERIODS_PER_DAY = 8


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


def make_placement(day="MON", start_period=1, venue_id=1, capacity=50, venue_type="LECTURE_HALL"):
    return Placement(
        day=day, start_period=start_period,
        venue_id=venue_id, venue_capacity=capacity, venue_type=venue_type,
    )


def scheduled(session, placement):
    return ScheduledSession(session=session, placement=placement)


# --- H1: Lecturer clash ---

def test_h1_no_clash_different_day():
    s = make_session(lecturer_id=1)
    p_new = make_placement(day="TUE", start_period=1)
    existing = scheduled(make_session(id=2, lecturer_id=1), make_placement(day="MON", start_period=1))
    assert h1_lecturer_clash(s, p_new, [existing]) is True


def test_h1_no_clash_different_lecturer():
    s = make_session(lecturer_id=2)
    p_new = make_placement(day="MON", start_period=1)
    existing = scheduled(make_session(lecturer_id=1), make_placement(day="MON", start_period=1))
    assert h1_lecturer_clash(s, p_new, [existing]) is True


def test_h1_clash_same_slot():
    s = make_session(lecturer_id=1)
    p_new = make_placement(day="MON", start_period=1)
    existing = scheduled(make_session(id=2, lecturer_id=1), make_placement(day="MON", start_period=1))
    assert h1_lecturer_clash(s, p_new, [existing]) is False


def test_h1_clash_overlap_multi_period():
    s = make_session(lecturer_id=1, session_length=2)
    p_new = make_placement(day="MON", start_period=2)
    existing = scheduled(
        make_session(id=2, lecturer_id=1, session_length=2),
        make_placement(day="MON", start_period=1),
    )
    assert h1_lecturer_clash(s, p_new, [existing]) is False


# --- H2: Venue clash ---

def test_h2_no_clash_different_venue():
    s = make_session()
    p_new = make_placement(day="MON", start_period=1, venue_id=2)
    existing = scheduled(make_session(id=2), make_placement(day="MON", start_period=1, venue_id=1))
    assert h2_venue_clash(s, p_new, [existing]) is True


def test_h2_clash_same_venue_same_slot():
    s = make_session()
    p_new = make_placement(day="MON", start_period=1, venue_id=1)
    existing = scheduled(make_session(id=2, course_id=2, lecturer_id=2), make_placement(day="MON", start_period=1, venue_id=1))
    assert h2_venue_clash(s, p_new, [existing]) is False


# --- H3: Course clash ---

def test_h3_same_course_different_slots():
    s = make_session(course_id=1)
    p_new = make_placement(day="MON", start_period=2)
    existing = scheduled(make_session(id=2, course_id=1), make_placement(day="MON", start_period=1))
    assert h3_course_clash(s, p_new, [existing]) is True


def test_h3_same_course_same_slot():
    s = make_session(course_id=1)
    p_new = make_placement(day="MON", start_period=1)
    existing = scheduled(make_session(id=2, course_id=1), make_placement(day="MON", start_period=1))
    assert h3_course_clash(s, p_new, [existing]) is False


# --- H4: Venue capacity ---

def test_h4_capacity_ok():
    s = make_session(class_size=30)
    p = make_placement(capacity=50)
    assert h4_venue_capacity(s, p) is True


def test_h4_capacity_exact():
    s = make_session(class_size=50)
    p = make_placement(capacity=50)
    assert h4_venue_capacity(s, p) is True


def test_h4_capacity_insufficient():
    s = make_session(class_size=51)
    p = make_placement(capacity=50)
    assert h4_venue_capacity(s, p) is False


# --- H5: Lecturer availability ---

def test_h5_available():
    s = make_session(unavailable=[("TUE", 3)])
    p = make_placement(day="MON", start_period=1)
    assert h5_lecturer_availability(s, p) is True


def test_h5_unavailable_single_period():
    s = make_session(unavailable=[("MON", 1)])
    p = make_placement(day="MON", start_period=1)
    assert h5_lecturer_availability(s, p) is False


def test_h5_unavailable_overlapping_multi_period():
    s = make_session(session_length=2, unavailable=[("MON", 2)])
    p = make_placement(day="MON", start_period=1)
    assert h5_lecturer_availability(s, p) is False


# --- H6: Working hours overflow ---

def test_h6_fits():
    s = make_session(session_length=2)
    p = make_placement(start_period=7)
    assert h6_within_working_hours(s, p, PERIODS_PER_DAY) is True


def test_h6_overflow():
    s = make_session(session_length=2)
    p = make_placement(start_period=8)
    assert h6_within_working_hours(s, p, PERIODS_PER_DAY) is False


# --- Soft score increases on S1 back-to-back ---

def test_s1_back_to_back_penalised():
    s = make_session(id=2, lecturer_id=1)
    existing_placement = make_placement(day="MON", start_period=1)
    existing = scheduled(make_session(lecturer_id=1), existing_placement)
    p_adjacent = make_placement(day="MON", start_period=2)
    p_gap = make_placement(day="MON", start_period=3, venue_id=2)

    score_adjacent = soft_score(s, p_adjacent, [existing], {}, PERIODS_PER_DAY)
    score_gap = soft_score(s, p_gap, [existing], {}, PERIODS_PER_DAY)

    assert score_adjacent > score_gap


# --- Soft score S4 late period penalised ---

def test_s4_late_period_penalised():
    s = make_session()
    p_early = make_placement(start_period=1)
    p_late = make_placement(start_period=8, venue_id=2)

    score_early = soft_score(s, p_early, [], {}, PERIODS_PER_DAY)
    score_late = soft_score(s, p_late, [], {}, PERIODS_PER_DAY)

    assert score_late > score_early
