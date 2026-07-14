"""Seed command: creates a realistic Computer Science department dataset.

Idempotent — safe to run multiple times. Use for demos and evaluation experiments.

Usage:
    python manage.py seed
    python manage.py seed --clear   # wipe and re-seed
"""
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Department, AcademicSession, Period, Day
from catalog.models import (
    Venue, VenueType, Lecturer, LecturerUnavailability, Course, CourseLecturer,
)


PERIODS = [
    (1, "Period 1",  "08:00", "09:00"),
    (2, "Period 2",  "09:00", "10:00"),
    (3, "Period 3",  "10:00", "11:00"),
    (4, "Period 4",  "11:00", "12:00"),
    (5, "Period 5",  "13:00", "14:00"),
    (6, "Period 6",  "14:00", "15:00"),
    (7, "Period 7",  "15:00", "16:00"),
    (8, "Period 8",  "16:00", "17:00"),
]

VENUES = [
    ("LH-101", 200, VenueType.LECTURE_HALL, "Main Block"),
    ("LH-102", 150, VenueType.LECTURE_HALL, "Main Block"),
    ("LH-103", 100, VenueType.LECTURE_HALL, "Main Block"),
    ("LH-201", 80,  VenueType.LECTURE_HALL, "Main Block"),
    ("SR-001", 40,  VenueType.SEMINAR,      "Annex Block"),
    ("SR-002", 40,  VenueType.SEMINAR,      "Annex Block"),
    ("LAB-A",  50,  VenueType.LAB,          "Engineering Block"),
    ("LAB-B",  50,  VenueType.LAB,          "Engineering Block"),
    ("LAB-C",  30,  VenueType.LAB,          "Engineering Block"),
]

COURSES = [
    # (code, title, credits, class_size, weekly_sessions, session_length, venue_type)
    ("CS101", "Introduction to Computing",          3, 180, 2, 1, VenueType.LECTURE_HALL),
    ("CS102", "Programming Fundamentals",           3, 160, 2, 1, VenueType.LECTURE_HALL),
    ("CS201", "Data Structures & Algorithms",       3, 120, 2, 1, VenueType.LECTURE_HALL),
    ("CS202", "Computer Organisation",              3, 100, 2, 1, VenueType.LECTURE_HALL),
    ("CS203", "Discrete Mathematics",               3, 130, 2, 1, VenueType.LECTURE_HALL),
    ("CS301", "Operating Systems",                  3,  80, 2, 1, VenueType.LECTURE_HALL),
    ("CS302", "Database Systems",                   3,  90, 2, 1, VenueType.LECTURE_HALL),
    ("CS303", "Computer Networks",                  3,  75, 2, 1, VenueType.LECTURE_HALL),
    ("CS401", "Software Engineering",               3,  60, 2, 1, VenueType.SEMINAR),
    ("CS402", "Artificial Intelligence",            3,  70, 2, 1, VenueType.LECTURE_HALL),
    ("CS403", "Web Technologies",                   3,  55, 2, 1, VenueType.SEMINAR),
    ("CS-LAB1", "Programming Lab I",               1,  40, 2, 2, VenueType.LAB),
    ("CS-LAB2", "Programming Lab II",              1,  40, 2, 2, VenueType.LAB),
    ("CS-LAB3", "Database Lab",                    1,  35, 2, 2, VenueType.LAB),
    ("CS-LAB4", "Networks Lab",                    1,  30, 2, 2, VenueType.LAB),
]

LECTURERS = [
    ("Dr. Amina Yusuf",    "a.yusuf@university.edu"),
    ("Prof. Bello Ibrahim", "b.ibrahim@university.edu"),
    ("Dr. Chiamaka Obi",   "c.obi@university.edu"),
    ("Mr. David Eze",       "d.eze@university.edu"),
    ("Dr. Emeka Nwosu",    "e.nwosu@university.edu"),
    ("Prof. Fatima Al-Hassan", "f.alhassan@university.edu"),
    ("Dr. Gbenga Adeyemi", "g.adeyemi@university.edu"),
]

# (course_code, lecturer_email)
ASSIGNMENTS = [
    ("CS101",  "a.yusuf@university.edu"),
    ("CS102",  "a.yusuf@university.edu"),
    ("CS201",  "b.ibrahim@university.edu"),
    ("CS202",  "b.ibrahim@university.edu"),
    ("CS203",  "f.alhassan@university.edu"),
    ("CS301",  "c.obi@university.edu"),
    ("CS302",  "d.eze@university.edu"),
    ("CS303",  "e.nwosu@university.edu"),
    ("CS401",  "g.adeyemi@university.edu"),
    ("CS402",  "f.alhassan@university.edu"),
    ("CS403",  "g.adeyemi@university.edu"),
    ("CS-LAB1","a.yusuf@university.edu"),
    ("CS-LAB2","c.obi@university.edu"),
    ("CS-LAB3","d.eze@university.edu"),
    ("CS-LAB4","e.nwosu@university.edu"),
]

# Unavailability: (lecturer_email, day, period_indices)
UNAVAILABILITIES = [
    ("a.yusuf@university.edu",      Day.MON, [1, 2]),
    ("b.ibrahim@university.edu",    Day.FRI, [7, 8]),
    ("c.obi@university.edu",        Day.WED, [5, 6]),
    ("d.eze@university.edu",        Day.TUE, [1]),
    ("e.nwosu@university.edu",      Day.THU, [7, 8]),
    ("f.alhassan@university.edu",   Day.MON, [7, 8]),
    ("g.adeyemi@university.edu",    Day.FRI, [1, 2]),
]


class Command(BaseCommand):
    help = "Seed the database with a realistic CS department dataset."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing seed data before seeding.")

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()
        with transaction.atomic():
            self._seed()
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _clear(self):
        self.stdout.write("Clearing existing data…")
        CourseLecturer.objects.all().delete()
        LecturerUnavailability.objects.all().delete()
        Course.objects.all().delete()
        Lecturer.objects.all().delete()
        Venue.objects.all().delete()
        Department.objects.filter(code="CS").delete()
        AcademicSession.objects.all().delete()
        Period.objects.all().delete()

    def _seed(self):
        # Periods
        for idx, label, start, end in PERIODS:
            Period.objects.get_or_create(
                index=idx,
                defaults={
                    "label": label,
                    "start_time": datetime.time.fromisoformat(start),
                    "end_time": datetime.time.fromisoformat(end),
                },
            )
        self.stdout.write(f"  {Period.objects.count()} periods")

        # Department
        dept, _ = Department.objects.get_or_create(
            code="CS", defaults={"name": "Computer Science"}
        )
        self.stdout.write(f"  Department: {dept}")

        # Academic session (active)
        session, _ = AcademicSession.objects.get_or_create(
            name="2025/2026",
            semester=AcademicSession.Semester.FIRST,
            defaults={"is_active": True},
        )
        # Ensure it's active
        if not session.is_active:
            session.is_active = True
            session.save()
        self.stdout.write(f"  Session: {session}")

        # Venues
        for name, cap, vtype, loc in VENUES:
            Venue.objects.get_or_create(
                name=name,
                defaults={"capacity": cap, "venue_type": vtype, "location": loc},
            )
        self.stdout.write(f"  {Venue.objects.count()} venues")

        # Lecturers
        for name, email in LECTURERS:
            Lecturer.objects.get_or_create(
                email=email, defaults={"name": name, "department": dept}
            )
        self.stdout.write(f"  {Lecturer.objects.count()} lecturers")

        # Unavailabilities
        periods = {p.index: p for p in Period.objects.all()}
        for email, day, period_idxs in UNAVAILABILITIES:
            try:
                lecturer = Lecturer.objects.get(email=email)
            except Lecturer.DoesNotExist:
                continue
            for pidx in period_idxs:
                if pidx in periods:
                    LecturerUnavailability.objects.get_or_create(
                        lecturer=lecturer, day=day, period=periods[pidx]
                    )

        # Courses
        for code, title, credits, size, weekly, length, vtype in COURSES:
            Course.objects.get_or_create(
                code=code,
                academic_session=session,
                defaults={
                    "title": title,
                    "credit_units": credits,
                    "department": dept,
                    "class_size": size,
                    "weekly_sessions": weekly,
                    "session_length": length,
                    "required_venue_type": vtype,
                },
            )
        self.stdout.write(f"  {Course.objects.count()} courses")

        # Lecturer assignments
        for code, email in ASSIGNMENTS:
            try:
                course = Course.objects.get(code=code, academic_session=session)
                lecturer = Lecturer.objects.get(email=email)
                CourseLecturer.objects.get_or_create(course=course, lecturer=lecturer)
            except (Course.DoesNotExist, Lecturer.DoesNotExist):
                self.stdout.write(self.style.WARNING(f"  Skipped assignment {code} → {email}"))

        self.stdout.write(f"  {CourseLecturer.objects.count()} course-lecturer assignments")
