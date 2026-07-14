from django.db import models
from core.models import Department, AcademicSession, Day, Period


class VenueType(models.TextChoices):
    LECTURE_HALL = "LECTURE_HALL", "Lecture Hall"
    LAB = "LAB", "Laboratory"
    SEMINAR = "SEMINAR", "Seminar Room"


class Venue(models.Model):
    name = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField()
    venue_type = models.CharField(
        max_length=20, choices=VenueType.choices, default=VenueType.LECTURE_HALL
    )
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (cap. {self.capacity})"


class Lecturer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="lecturers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LecturerUnavailability(models.Model):
    lecturer = models.ForeignKey(
        Lecturer, on_delete=models.CASCADE, related_name="unavailabilities"
    )
    day = models.CharField(max_length=3, choices=Day.choices)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("lecturer", "day", "period")]

    def __str__(self):
        return f"{self.lecturer} unavailable {self.day} P{self.period.index}"


class Course(models.Model):
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    credit_units = models.PositiveSmallIntegerField(default=3)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="courses"
    )
    class_size = models.PositiveIntegerField(default=30)
    weekly_sessions = models.PositiveSmallIntegerField(default=2)
    session_length = models.PositiveSmallIntegerField(default=1)
    required_venue_type = models.CharField(
        max_length=20, choices=VenueType.choices, default=VenueType.LECTURE_HALL
    )
    academic_session = models.ForeignKey(
        AcademicSession, on_delete=models.CASCADE, related_name="courses"
    )
    lecturers = models.ManyToManyField(
        Lecturer, through="CourseLecturer", related_name="courses", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("code", "academic_session")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.title}"


class CourseLecturer(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="course_lecturers"
    )
    lecturer = models.ForeignKey(
        Lecturer, on_delete=models.CASCADE, related_name="course_lecturers"
    )

    class Meta:
        unique_together = [("course", "lecturer")]

    def __str__(self):
        return f"{self.lecturer} → {self.course}"
