from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from scheduling.models import Timetable
from . import pdf as pdf_module, excel as excel_module


@login_required
def export_pdf(request, pk):
    timetable = get_object_or_404(
        Timetable.objects.select_related("academic_session"), pk=pk
    )
    try:
        pdf_bytes = pdf_module.generate_pdf(
            timetable, base_url=request.build_absolute_uri("/")
        )
    except ImportError:
        return HttpResponse(
            "PDF export requires WeasyPrint system libraries.\n"
            "Run `docker compose up` — the Docker container has everything set up.",
            status=501,
            content_type="text/plain",
        )
    safe_name = _safe_filename(timetable.name)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'
    return response


@login_required
def export_excel(request, pk):
    timetable = get_object_or_404(
        Timetable.objects.select_related("academic_session"), pk=pk
    )
    wb = excel_module.generate_excel(timetable)
    safe_name = _safe_filename(timetable.name)
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{safe_name}.xlsx"'
    wb.save(response)
    return response


def _safe_filename(name: str) -> str:
    return name.replace(" ", "-").replace("/", "-").replace("\\", "-")
