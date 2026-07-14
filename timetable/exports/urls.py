from django.urls import path
from . import views

app_name = "exports"

urlpatterns = [
    path("schedule/<int:pk>/export/pdf/", views.export_pdf, name="pdf"),
    path("schedule/<int:pk>/export/excel/", views.export_excel, name="excel"),
]
