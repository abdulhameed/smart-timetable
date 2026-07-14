from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from core.models import AcademicSession, Day, Period
from .models import Timetable, TimetableEntry
from . import services


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _build_grid_context(timetable: Timetable, filter_entries=None) -> dict:
    """Build the full grid data structure used by both the grid page and move responses."""
    periods = list(Period.objects.order_by("index"))
    day_choices = list(Day.choices)

    entries_qs = (
        filter_entries
        if filter_entries is not None
        else TimetableEntry.objects.filter(timetable=timetable).select_related(
            "course__department", "lecturer", "venue", "start_period"
        )
    )

    entry_map: dict = defaultdict(list)
    for e in entries_qs:
        entry_map[(e.day, e.start_period.index)].append(e)

    grid = [
        {
            "period": period,
            "cells": [
                {"day": day_val, "entries": entry_map.get((day_val, period.index), [])}
                for day_val, _ in day_choices
            ],
        }
        for period in periods
    ]
    return {"timetable": timetable, "grid": grid, "day_choices": day_choices}


# ---------------------------------------------------------------------------
# Timetable list
# ---------------------------------------------------------------------------

@login_required
def timetable_list(request):
    timetables = Timetable.objects.select_related("academic_session", "created_by")
    return render(request, "scheduling/timetable_list.html", {"timetables": timetables})


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

@role_required("ADMIN", "TIMETABLE_OFFICER")
def generate_page(request):
    sessions = AcademicSession.objects.all()
    active = sessions.filter(is_active=True).first()

    if request.method == "POST":
        session_id = request.POST.get("session_id")
        greedy_only = request.POST.get("greedy_only") == "1"
        session = get_object_or_404(AcademicSession, pk=session_id)
        try:
            timetable, _ = services.run_generation(session, request.user, greedy_only=greedy_only)
            return redirect("scheduling:result", pk=timetable.pk)
        except ValueError as exc:
            messages.error(request, str(exc))

    return render(request, "scheduling/generate.html", {
        "sessions": sessions,
        "active_session": active,
    })


# ---------------------------------------------------------------------------
# Result summary
# ---------------------------------------------------------------------------

@login_required
def timetable_result(request, pk):
    timetable = get_object_or_404(
        Timetable.objects.select_related("academic_session", "created_by"), pk=pk
    )
    return render(request, "scheduling/result.html", {"timetable": timetable})


# ---------------------------------------------------------------------------
# Timetable grid
# ---------------------------------------------------------------------------

@login_required
def timetable_grid(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk)

    entries_qs = TimetableEntry.objects.filter(timetable=timetable).select_related(
        "course__department", "lecturer", "venue", "start_period"
    )

    dept_filter = request.GET.get("dept", "")
    lecturer_filter = request.GET.get("lecturer", "")
    venue_filter = request.GET.get("venue", "")

    if dept_filter:
        entries_qs = entries_qs.filter(course__department_id=dept_filter)
    if lecturer_filter:
        entries_qs = entries_qs.filter(lecturer_id=lecturer_filter)
    if venue_filter:
        entries_qs = entries_qs.filter(venue_id=venue_filter)

    from catalog.models import Lecturer, Venue
    from core.models import Department

    ctx = _build_grid_context(timetable, list(entries_qs))
    ctx.update({
        "dept_filter": dept_filter,
        "lecturer_filter": lecturer_filter,
        "venue_filter": venue_filter,
        "departments": Department.objects.filter(
            courses__timetableentry__timetable=timetable
        ).distinct(),
        "lecturers": Lecturer.objects.filter(
            timetableentry__timetable=timetable
        ).distinct(),
        "venues": Venue.objects.filter(
            timetableentry__timetable=timetable
        ).distinct(),
    })
    return render(request, "scheduling/grid.html", ctx)


# ---------------------------------------------------------------------------
# Move entry (Phase 3 — live validation)
# ---------------------------------------------------------------------------

@role_required("ADMIN", "TIMETABLE_OFFICER")
def entry_move(request, timetable_pk, entry_pk):
    if request.method != "POST":
        return HttpResponse(status=405)

    timetable = get_object_or_404(Timetable, pk=timetable_pk)
    if timetable.status != Timetable.Status.DRAFT:
        return HttpResponse("This timetable is read-only.", status=403)

    entry = get_object_or_404(TimetableEntry, pk=entry_pk, timetable=timetable)

    new_day = request.POST.get("day", "").strip().upper()
    try:
        new_period_index = int(request.POST.get("period_index", 0))
        new_venue_id = int(request.POST.get("venue_id") or entry.venue_id)
    except (ValueError, TypeError):
        return render(request, "scheduling/partials/_move_error.html",
                      {"error": "Invalid move parameters."})

    if not new_day or new_period_index < 1:
        return render(request, "scheduling/partials/_move_error.html",
                      {"error": "Missing day or period."})

    # Validate against H1–H6 before touching the database
    error = services.validate_move(entry, new_day, new_period_index, new_venue_id)
    if error:
        return render(request, "scheduling/partials/_move_error.html", {"error": error})

    try:
        new_period = Period.objects.get(index=new_period_index)
    except Period.DoesNotExist:
        return render(request, "scheduling/partials/_move_error.html",
                      {"error": f"Period {new_period_index} does not exist."})

    # Commit
    entry.day = new_day
    entry.start_period = new_period
    entry.venue_id = new_venue_id
    entry.save()

    ctx = _build_grid_context(timetable)
    return render(request, "scheduling/partials/_move_success.html", ctx)


# ---------------------------------------------------------------------------
# Conflicts panel partial (HTMX refresh)
# ---------------------------------------------------------------------------

@login_required
def conflicts_panel(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk)
    return render(request, "scheduling/partials/_conflicts_panel.html",
                  {"timetable": timetable})


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

@role_required("ADMIN", "TIMETABLE_OFFICER")
def timetable_publish(request, pk):
    if request.method != "POST":
        return HttpResponse(status=405)

    timetable = get_object_or_404(Timetable, pk=pk)

    if timetable.status != Timetable.Status.DRAFT:
        messages.error(request, "Only draft timetables can be published.")
        return redirect("scheduling:result", pk=pk)

    if timetable.hard_violations > 0:
        messages.error(
            request,
            f"Cannot publish: {timetable.hard_violations} hard constraint violation(s) must be resolved first.",
        )
        return redirect("scheduling:result", pk=pk)

    timetable.status = Timetable.Status.PUBLISHED
    timetable.save()
    messages.success(request, f"'{timetable.name}' published successfully.")
    return redirect("scheduling:result", pk=pk)
