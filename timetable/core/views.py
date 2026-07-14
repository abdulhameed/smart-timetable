from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from accounts.decorators import role_required
from .forms import DepartmentForm, PeriodForm
from .models import Department, AcademicSession, Period


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    from catalog.models import Course, Lecturer, Venue
    active_session = AcademicSession.objects.filter(is_active=True).first()
    context = {
        "course_count": Course.objects.filter(academic_session=active_session).count() if active_session else 0,
        "lecturer_count": Lecturer.objects.count(),
        "venue_count": Venue.objects.count(),
        "active_session": active_session,
    }
    return render(request, "core/dashboard.html", context)


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

@role_required("ADMIN")
def department_list(request):
    qs = Department.objects.all()
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q)
    return render(request, "core/department_list.html", {"departments": qs, "q": q})


@role_required("ADMIN")
def department_table(request):
    qs = Department.objects.all()
    return render(request, "core/partials/_department_table.html", {"departments": qs})


@role_required("ADMIN")
def department_create(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshDepartments"
            return response
        return render(request, "core/partials/_department_form.html", {"form": form, "title": "New Department"})
    form = DepartmentForm()
    return render(request, "core/partials/_department_form.html", {"form": form, "title": "New Department"})


@role_required("ADMIN")
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshDepartments"
            return response
        return render(request, "core/partials/_department_form.html", {"form": form, "title": "Edit Department", "obj": dept})
    form = DepartmentForm(instance=dept)
    return render(request, "core/partials/_department_form.html", {"form": form, "title": "Edit Department", "obj": dept})


@role_required("ADMIN")
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        dept.delete()
        response = HttpResponse("")
        response["HX-Trigger"] = "refreshDepartments"
        return response
    return HttpResponse(status=405)


# ---------------------------------------------------------------------------
# Time configuration (Periods)
# ---------------------------------------------------------------------------

@role_required("ADMIN")
def time_config(request):
    periods = Period.objects.all()
    form = PeriodForm()
    return render(request, "core/time_config.html", {"periods": periods, "form": form})


@role_required("ADMIN")
def period_create(request):
    if request.method == "POST":
        form = PeriodForm(request.POST)
        if form.is_valid():
            form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = "refreshPeriods"
            return response
        return render(request, "core/partials/_period_form.html", {"form": form})
    form = PeriodForm()
    return render(request, "core/partials/_period_form.html", {"form": form})


@role_required("ADMIN")
def period_delete(request, pk):
    period = get_object_or_404(Period, pk=pk)
    if request.method == "POST":
        period.delete()
        response = HttpResponse("")
        response["HX-Trigger"] = "refreshPeriods"
        return response
    return HttpResponse(status=405)
