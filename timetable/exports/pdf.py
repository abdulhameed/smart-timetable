"""PDF export using WeasyPrint.

WeasyPrint renders an HTML template (with inline CSS) to A4-landscape PDF.
It requires system libraries (pango, cairo) — available in the Docker container.
Run `docker compose up` to use PDF export in local dev.
"""
from collections import defaultdict
from django.template.loader import render_to_string

from core.models import Day, Period
from scheduling.models import TimetableEntry


def _build_grid(timetable):
    periods = list(Period.objects.order_by("index"))
    day_choices = list(Day.choices)
    entries = TimetableEntry.objects.filter(timetable=timetable).select_related(
        "course__department", "lecturer", "venue", "start_period"
    )
    entry_map: dict = defaultdict(list)
    for e in entries:
        entry_map[(e.day, e.start_period.index)].append(e)

    grid = [
        {
            "period": period,
            "cells": [
                {"day": dv, "entries": entry_map.get((dv, period.index), [])}
                for dv, _ in day_choices
            ],
        }
        for period in periods
    ]
    return grid, day_choices


def generate_pdf(timetable, base_url: str = "") -> bytes:
    """Return PDF bytes for *timetable*. Raises ImportError if WeasyPrint unavailable."""
    from weasyprint import HTML  # deferred so server starts even if WeasyPrint missing

    grid, day_choices = _build_grid(timetable)
    html = render_to_string("exports/timetable_pdf.html", {
        "timetable": timetable,
        "grid": grid,
        "day_choices": day_choices,
    })
    return HTML(string=html, base_url=base_url or "/").write_pdf()
