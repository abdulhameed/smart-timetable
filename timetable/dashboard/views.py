import json
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from scheduling.models import Timetable, TimetableEntry
from .models import EvaluationBaseline
from .forms import EvaluationBaselineForm


@login_required
def evaluation_dashboard(request, pk):
    timetable = get_object_or_404(
        Timetable.objects.select_related("academic_session"), pk=pk
    )
    baseline, _ = EvaluationBaseline.objects.get_or_create(timetable=timetable)

    if request.method == "POST":
        form = EvaluationBaselineForm(request.POST, instance=baseline)
        if form.is_valid():
            form.save()
            return redirect("dashboard:evaluation", pk=pk)
    else:
        form = EvaluationBaselineForm(instance=baseline)

    metrics = timetable.metrics
    per_day = metrics.get("per_day_counts", {})

    # Per-lecturer back-to-back breakdown for the detail table
    entries = TimetableEntry.objects.filter(timetable=timetable).select_related(
        "lecturer", "start_period"
    )
    lect_segs: dict = defaultdict(list)
    for e in entries:
        lect_segs[(e.lecturer.name, e.day)].append((e.start_period.index, e.length))

    lect_btb: dict = defaultdict(int)
    for (name, _day), segs in lect_segs.items():
        segs.sort()
        for i in range(len(segs) - 1):
            end = segs[i][0] + segs[i][1]
            if end == segs[i + 1][0]:
                lect_btb[name] += 1

    return render(request, "dashboard/evaluation.html", {
        "timetable": timetable,
        "baseline": baseline,
        "form": form,
        "metrics": metrics,
        "chart_labels_json": json.dumps(list(per_day.keys())),
        "chart_values_json": json.dumps(list(per_day.values())),
        "btb_list": sorted(lect_btb.items(), key=lambda x: -x[1]),
    })
