"""Event API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.events.api.views import EventCategoryViewSet, EventImageViewSet, EventViewSet

router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("event-categories", EventCategoryViewSet, basename="event-category")
router.register("event-images", EventImageViewSet, basename="event-image")

app_name = "events_api"

urlpatterns = [path("", include(router.urls))]
