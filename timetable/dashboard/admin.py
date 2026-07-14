from django.contrib import admin
from .models import EvaluationBaseline


@admin.register(EvaluationBaseline)
class EvaluationBaselineAdmin(admin.ModelAdmin):
    list_display = ("timetable", "manual_conflicts", "manual_time_minutes", "manual_sessions_scheduled")
    readonly_fields = ("created_at", "updated_at")
