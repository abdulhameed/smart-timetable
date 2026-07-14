from django.urls import path
from . import views

app_name = "scheduling"

urlpatterns = [
    path("schedule/", views.timetable_list, name="list"),
    path("schedule/generate/", views.generate_page, name="generate"),
    path("schedule/<int:pk>/", views.timetable_result, name="result"),
    path("schedule/<int:pk>/grid/", views.timetable_grid, name="grid"),
    path("schedule/<int:pk>/publish/", views.timetable_publish, name="publish"),
    path("schedule/<int:pk>/conflicts/", views.conflicts_panel, name="conflicts-panel"),
    path("schedule/<int:timetable_pk>/entries/<int:entry_pk>/move/", views.entry_move, name="entry-move"),
]
