from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),
    path("", include("catalog.urls")),
    path("", include("scheduling.urls")),
    path("", include("exports.urls")),
    path("", include("dashboard.urls")),
]
