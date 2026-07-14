from django.contrib import admin
from .models import Department, AcademicSession, Period


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "semester", "is_active")
    list_filter = ("is_active", "semester")


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ("index", "label", "start_time", "end_time")
    ordering = ("index",)
