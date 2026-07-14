from django.db import models


class Day(models.TextChoices):
    MON = "MON", "Monday"
    TUE = "TUE", "Tuesday"
    WED = "WED", "Wednesday"
    THU = "THU", "Thursday"
    FRI = "FRI", "Friday"


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class AcademicSession(models.Model):
    class Semester(models.TextChoices):
        FIRST = "FIRST", "First Semester"
        SECOND = "SECOND", "Second Semester"

    name = models.CharField(max_length=20)       # e.g. "2025/2026"
    semester = models.CharField(max_length=10, choices=Semester.choices)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("name", "semester")]
        ordering = ["-name", "semester"]

    def __str__(self):
        return f"{self.name} — {self.get_semester_display()}"

    def save(self, *args, **kwargs):
        # Enforce single active session
        if self.is_active:
            AcademicSession.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class Period(models.Model):
    index = models.PositiveSmallIntegerField(unique=True)  # 1-indexed
    label = models.CharField(max_length=20)                # e.g. "Period 1"
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["index"]

    def __str__(self):
        return f"{self.label} ({self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')})"
