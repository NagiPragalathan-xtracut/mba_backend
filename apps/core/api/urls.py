"""Core API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.api.feed import (
    news_events_categories,
    news_events_courses,
    news_events_detail,
    news_events_feed,
)
from apps.core.api.views import CourseViewSet, DepartmentViewSet, health_check

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("courses", CourseViewSet, basename="course")

app_name = "core_api"

urlpatterns = [
    path("health/", health_check, name="health"),
    # The common feed. `categories/` is declared before the catch-all detail
    # route so it is not swallowed as an identifier named "categories".
    path("news-events/categories/", news_events_categories, name="news-events-categories"),
    path("news-events/courses/", news_events_courses, name="news-events-courses"),
    path("news-events/<str:identifier>/", news_events_detail, name="news-events-detail"),
    path("news-events/", news_events_feed, name="news-events"),
    path("", include(router.urls)),
]
