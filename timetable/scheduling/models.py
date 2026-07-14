from django.conf import settings
from django.db import models

from core.models import AcademicSession, Day, Period
from catalog.models import Course, Lecturer, Venue


class Timetable(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    name = models.CharField(max_length=150)
    academic_session = models.ForeignKey(
        AcademicSession, on_delete=models.CASCADE, related_name="timetables"
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    soft_score = models.IntegerField(default=0)
    generation_time_ms = models.IntegerField(default=0)
    # Stores metrics + normalised unscheduled list from the engine
    metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} [{self.get_status_display()}]"

    @property
    def scheduled_count(self):
        return self.metrics.get("scheduled_count", self.entries.count())

    @property
    def unscheduled_count(self):
        return self.metrics.get("unscheduled_count", 0)

    @property
    def unscheduled_list(self):
        return self.metrics.get("unscheduled", [])

    @property
    def hard_violations(self):
        # Engine guarantees zero; Phase 3 stores violations when manual edits happen
        return self.metrics.get("hard_violations", 0)

    def can_publish(self):
        return self.hard_violations == 0 and self.status == self.Status.DRAFT


class TimetableEntry(models.Model):
    timetable = models.ForeignKey(
        Timetable, on_delete=models.CASCADE, related_name="entries"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=Day.choices)
    start_period = models.ForeignKey(Period, on_delete=models.CASCADE)
    length = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day", "start_period__index"]

    def __str__(self):
        return f"{self.course.code} | {self.day} P{self.start_period.index} | {self.venue.name}"

    @property
    def end_period_index(self):
        return self.start_period.index + self.length - 1
