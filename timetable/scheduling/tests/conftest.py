"""Pytest fixtures for scheduling integration tests."""
import datetime
import pytest

from accounts.models import User
from catalog.models import Course, CourseLecturer, Lecturer, Venue
from core.models import AcademicSession, Department, Period
from scheduling.models import Timetable, TimetableEntry


@pytest.fixture
def dept(db):
    return Department.objects.create(name="Computer Science", code="CS")


@pytest.fixture
def session(db):
    return AcademicSession.objects.create(
        name="2025/2026", semester=AcademicSession.Semester.FIRST, is_active=True
    )


@pytest.fixture
def periods(db):
    return [
        Period.objects.create(
            index=i,
            label=f"Period {i}",
            start_time=datetime.time(7 + i, 0),
            end_time=datetime.time(8 + i, 0),
        )
        for i in range(1, 5)
    ]


@pytest.fixture
def venue(db):
    return Venue.objects.create(name="LH-001", capacity=100, venue_type="LECTURE_HALL")


@pytest.fixture
def venue2(db):
    return Venue.objects.create(name="LH-002", capacity=100, venue_type="LECTURE_HALL")


@pytest.fixture
def lecturer(db, dept):
    return Lecturer.objects.create(name="Dr. Test", email="test@uni.edu", department=dept)


@pytest.fixture
def course(db, dept, session):
    return Course.objects.create(
        code="CS101", title="Test Course", department=dept,
        class_size=50, academic_session=session,
        weekly_sessions=1, session_length=1, required_venue_type="LECTURE_HALL",
    )


@pytest.fixture
def course2(db, dept, session):
    return Course.objects.create(
        code="CS102", title="Other Course", department=dept,
        class_size=50, academic_session=session,
        weekly_sessions=1, session_length=1, required_venue_type="LECTURE_HALL",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user("admin", password="pass", role="ADMIN")


@pytest.fixture
def officer_user(db):
    return User.objects.create_user("officer", password="pass", role="TIMETABLE_OFFICER")


@pytest.fixture
def viewer_user(db):
    return User.objects.create_user("viewer", password="pass", role="VIEWER")


@pytest.fixture
def draft_timetable(db, session, admin_user):
    return Timetable.objects.create(
        name="Test Draft",
        academic_session=session,
        status=Timetable.Status.DRAFT,
        created_by=admin_user,
        metrics={"scheduled_count": 0, "unscheduled_count": 0, "unscheduled": []},
    )


@pytest.fixture
def entry(db, draft_timetable, course, lecturer, venue, periods):
    """A single entry at MON/Period-1."""
    return TimetableEntry.objects.create(
        timetable=draft_timetable,
        course=course,
        lecturer=lecturer,
        venue=venue,
        day="MON",
        start_period=periods[0],
        length=1,
    )


@pytest.fixture
def entry2(db, draft_timetable, course2, lecturer, venue2, periods):
    """A second entry (same lecturer) at TUE/Period-1 — used to test clash."""
    return TimetableEntry.objects.create(
        timetable=draft_timetable,
        course=course2,
        lecturer=lecturer,
        venue=venue2,
        day="TUE",
        start_period=periods[0],
        length=1,
    )
