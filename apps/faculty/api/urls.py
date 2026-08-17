"""Faculty API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.faculty.api.views import (
    DesignationViewSet,
    FacultyBannerViewSet,
    FacultySectionViewSet,
    FacultyViewSet,
)

router = DefaultRouter()
router.register("faculty", FacultyViewSet, basename="faculty")
router.register("designations", DesignationViewSet, basename="designation")
router.register("faculty-sections", FacultySectionViewSet, basename="faculty-section")
router.register("faculty-banners", FacultyBannerViewSet, basename="faculty-banner")

app_name = "faculty_api"

urlpatterns = [path("", include(router.urls))]
