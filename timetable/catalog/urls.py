from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    # Venues
    path("venues/", views.venue_list, name="venue-list"),
    path("venues/table/", views.venue_table, name="venue-table"),
    path("venues/create/", views.venue_create, name="venue-create"),
    path("venues/<int:pk>/edit/", views.venue_edit, name="venue-edit"),
    path("venues/<int:pk>/delete/", views.venue_delete, name="venue-delete"),
    # Lecturers
    path("lecturers/", views.lecturer_list, name="lecturer-list"),
    path("lecturers/table/", views.lecturer_table, name="lecturer-table"),
    path("lecturers/create/", views.lecturer_create, name="lecturer-create"),
    path("lecturers/<int:pk>/edit/", views.lecturer_edit, name="lecturer-edit"),
    path("lecturers/<int:pk>/delete/", views.lecturer_delete, name="lecturer-delete"),
    path("lecturers/<int:pk>/availability/", views.lecturer_availability, name="lecturer-availability"),
    path("lecturers/<int:pk>/availability/toggle/", views.lecturer_availability_toggle, name="lecturer-availability-toggle"),
    # Courses
    path("courses/", views.course_list, name="course-list"),
    path("courses/table/", views.course_table, name="course-table"),
    path("courses/create/", views.course_create, name="course-create"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course-edit"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course-delete"),
]
