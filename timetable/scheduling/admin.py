from django.contrib import admin
from .models import Timetable, TimetableEntry


class TimetableEntryInline(admin.TabularInline):
    model = TimetableEntry
    extra = 0
    readonly_fields = ("course", "lecturer", "venue", "day", "start_period", "length")
    can_delete = False


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_session", "status", "soft_score", "generation_time_ms", "generated_at")
    list_filter = ("status", "academic_session")
    readonly_fields = ("generated_at", "soft_score", "generation_time_ms", "metrics", "created_at", "updated_at")
    inlines = [TimetableEntryInline]
