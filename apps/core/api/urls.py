"""Core API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.api.views import DepartmentViewSet, health_check

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")

app_name = "core_api"

urlpatterns = [
    path("health/", health_check, name="health"),
    path("", include(router.urls)),
]
