from django.contrib import admin
from .models import Venue, Lecturer, LecturerUnavailability, Course, CourseLecturer


class CourseLecturerInline(admin.TabularInline):
    model = CourseLecturer
    extra = 1


class LecturerUnavailabilityInline(admin.TabularInline):
    model = LecturerUnavailability
    extra = 0


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "venue_type", "capacity", "location")
    list_filter = ("venue_type",)
    search_fields = ("name",)


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "department")
    list_filter = ("department",)
    search_fields = ("name", "email")
    inlines = [LecturerUnavailabilityInline]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "department", "class_size", "weekly_sessions", "academic_session")
    list_filter = ("department", "academic_session", "required_venue_type")
    search_fields = ("code", "title")
    inlines = [CourseLecturerInline]
