from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    TIMETABLE_OFFICER = "TIMETABLE_OFFICER", "Timetable Officer"
    VIEWER = "VIEWER", "Viewer"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_officer(self):
        return self.role in (Role.ADMIN, Role.TIMETABLE_OFFICER)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
