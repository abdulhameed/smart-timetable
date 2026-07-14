from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Departments
    path("departments/", views.department_list, name="department-list"),
    path("departments/table/", views.department_table, name="department-table"),
    path("departments/create/", views.department_create, name="department-create"),
    path("departments/<int:pk>/edit/", views.department_edit, name="department-edit"),
    path("departments/<int:pk>/delete/", views.department_delete, name="department-delete"),
    # Time config
    path("time-config/", views.time_config, name="time-config"),
    path("time-config/periods/create/", views.period_create, name="period-create"),
    path("time-config/periods/<int:pk>/delete/", views.period_delete, name="period-delete"),
]
