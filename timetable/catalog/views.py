from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from accounts.decorators import role_required
from core.models import Day, Period
from .forms import VenueForm, LecturerForm, CourseForm
from .models import Venue, Lecturer, LecturerUnavailability, Course


# ---------------------------------------------------------------------------
# Venues
# ---------------------------------------------------------------------------

@login_required
def venue_list(request):
    qs = Venue.objects.all()
    q = request.GET.get("q", "")
    vtype = request.GET.get("type", "")
    if q:
        qs = qs.filter(name__icontains=q)
    if vtype:
        qs = qs.filter(venue_type=vtype)
    from .models import VenueType
    return render(request, "catalog/venue_list.html", {
        "venues": qs, "q": q, "vtype": vtype, "venue_types": VenueType.choices
    })


@login_required
def venue_table(request):
    return render(request, "catalog/partials/_venue_table.html", {"venues": Venue.objects.all()})


@role_required("ADMIN", "TIMETABLE_OFFICER")
def venue_create(request):
    if request.method == "POST":
        form = VenueForm(request.POST)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshVenues"
            return response
        return render(request, "catalog/partials/_venue_form.html", {"form": form, "title": "New Venue"})
    return render(request, "catalog/partials/_venue_form.html", {"form": VenueForm(), "title": "New Venue"})


@role_required("ADMIN", "TIMETABLE_OFFICER")
def venue_edit(request, pk):
    venue = get_object_or_404(Venue, pk=pk)
    if request.method == "POST":
        form = VenueForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshVenues"
            return response
        return render(request, "catalog/partials/_venue_form.html", {"form": form, "title": "Edit Venue", "obj": venue})
    return render(request, "catalog/partials/_venue_form.html", {"form": VenueForm(instance=venue), "title": "Edit Venue", "obj": venue})


@role_required("ADMIN", "TIMETABLE_OFFICER")
def venue_delete(request, pk):
    venue = get_object_or_404(Venue, pk=pk)
    if request.method == "POST":
        venue.delete()
        response = HttpResponse("")
        response["HX-Trigger"] = "refreshVenues"
        return response
    return HttpResponse(status=405)


# ---------------------------------------------------------------------------
# Lecturers
# ---------------------------------------------------------------------------

@login_required
def lecturer_list(request):
    qs = Lecturer.objects.select_related("department")
    q = request.GET.get("q", "")
    dept = request.GET.get("dept", "")
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(email__icontains=q)
    if dept:
        qs = qs.filter(department_id=dept)
    from core.models import Department
    return render(request, "catalog/lecturer_list.html", {
        "lecturers": qs, "q": q, "dept": dept,
        "departments": Department.objects.all(),
    })


@login_required
def lecturer_table(request):
    return render(request, "catalog/partials/_lecturer_table.html", {
        "lecturers": Lecturer.objects.select_related("department")
    })


@role_required("ADMIN", "TIMETABLE_OFFICER")
def lecturer_create(request):
    if request.method == "POST":
        form = LecturerForm(request.POST)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshLecturers"
            return response
        return render(request, "catalog/partials/_lecturer_form.html", {"form": form, "title": "New Lecturer"})
    return render(request, "catalog/partials/_lecturer_form.html", {"form": LecturerForm(), "title": "New Lecturer"})


@role_required("ADMIN", "TIMETABLE_OFFICER")
def lecturer_edit(request, pk):
    lecturer = get_object_or_404(Lecturer, pk=pk)
    if request.method == "POST":
        form = LecturerForm(request.POST, instance=lecturer)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshLecturers"
            return response
        return render(request, "catalog/partials/_lecturer_form.html", {"form": form, "title": "Edit Lecturer", "obj": lecturer})
    return render(request, "catalog/partials/_lecturer_form.html", {
        "form": LecturerForm(instance=lecturer), "title": "Edit Lecturer", "obj": lecturer
    })


@role_required("ADMIN", "TIMETABLE_OFFICER")
def lecturer_delete(request, pk):
    lecturer = get_object_or_404(Lecturer, pk=pk)
    if request.method == "POST":
        lecturer.delete()
        response = HttpResponse("")
        response["HX-Trigger"] = "refreshLecturers"
        return response
    return HttpResponse(status=405)


@role_required("ADMIN", "TIMETABLE_OFFICER")
def lecturer_availability(request, pk):
    lecturer = get_object_or_404(Lecturer, pk=pk)
    periods = list(Period.objects.all())
    blocked_pairs = set(
        lecturer.unavailabilities.values_list("day", "period_id")
    )
    # Pre-build grid so templates don't need tuple logic
    grid = [
        {
            "day_val": day_val,
            "day_label": day_label,
            "cells": [
                {
                    "day": day_val,
                    "period": period,
                    "blocked": (day_val, period.pk) in blocked_pairs,
                }
                for period in periods
            ],
        }
        for day_val, day_label in Day.choices
    ]
    return render(request, "catalog/lecturer_availability.html", {
        "lecturer": lecturer,
        "periods": periods,
        "grid": grid,
    })


@role_required("ADMIN", "TIMETABLE_OFFICER")
def lecturer_availability_toggle(request, pk):
    """Toggle a single day×period cell for a lecturer's unavailability."""
    if request.method != "POST":
        return HttpResponse(status=405)
    lecturer = get_object_or_404(Lecturer, pk=pk)
    day = request.POST.get("day")
    period_id = request.POST.get("period_id")
    period = get_object_or_404(Period, pk=period_id)

    obj, created = LecturerUnavailability.objects.get_or_create(
        lecturer=lecturer, day=day, period=period
    )
    if not created:
        obj.delete()
        blocked = False
    else:
        blocked = True

    return render(request, "catalog/partials/_availability_cell.html", {
        "lecturer": lecturer, "day": day, "period": period, "blocked": blocked,
    })


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

@login_required
def course_list(request):
    from core.models import AcademicSession, Department
    qs = Course.objects.select_related("department", "academic_session").prefetch_related("lecturers")
    q = request.GET.get("q", "")
    dept = request.GET.get("dept", "")
    session_id = request.GET.get("session", "")
    if q:
        qs = qs.filter(code__icontains=q) | qs.filter(title__icontains=q)
    if dept:
        qs = qs.filter(department_id=dept)
    if session_id:
        qs = qs.filter(academic_session_id=session_id)
    return render(request, "catalog/course_list.html", {
        "courses": qs, "q": q, "dept": dept, "session_id": session_id,
        "departments": Department.objects.all(),
        "sessions": AcademicSession.objects.all(),
    })


@login_required
def course_table(request):
    return render(request, "catalog/partials/_course_table.html", {
        "courses": Course.objects.select_related("department", "academic_session").prefetch_related("lecturers")
    })


@role_required("ADMIN", "TIMETABLE_OFFICER")
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshCourses"
            return response
        return render(request, "catalog/partials/_course_form.html", {"form": form, "title": "New Course"})
    return render(request, "catalog/partials/_course_form.html", {"form": CourseForm(), "title": "New Course"})


@role_required("ADMIN", "TIMETABLE_OFFICER")
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshCourses"
            return response
        return render(request, "catalog/partials/_course_form.html", {"form": form, "title": "Edit Course", "obj": course})
    return render(request, "catalog/partials/_course_form.html", {
        "form": CourseForm(instance=course), "title": "Edit Course", "obj": course
    })


@role_required("ADMIN", "TIMETABLE_OFFICER")
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        course.delete()
        response = HttpResponse("")
        response["HX-Trigger"] = "refreshCourses"
        return response
    return HttpResponse(status=405)
