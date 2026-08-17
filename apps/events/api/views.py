"""Event API endpoints."""

from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.api.viewsets import BaseContentViewSet, TaxonomyViewSet
from apps.events.api.filters import EventFilter
from apps.events.api.serializers import (
    EventCategorySerializer,
    EventImageSerializer,
    EventListSerializer,
    EventSerializer,
)
from apps.events.models import Event, EventCategory, EventImage


class EventCategoryViewSet(TaxonomyViewSet):
    """Event categories such as Upcoming and Achievements."""

    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    filterset_fields = ["is_active"]


@extend_schema_view(
    list=extend_schema(summary="List events", description="Public listing. Supports filtering by category, department and date range."),
    retrieve=extend_schema(summary="Retrieve one event by slug, id or UUID"),
    create=extend_schema(summary="Create an event (requires a token)"),
)
class EventViewSet(BaseContentViewSet):
    """Events and achievements."""

    queryset = (
        Event.objects.select_related("category")
        .prefetch_related("departments", "images")
        .all()
    )
    serializer_class = EventSerializer
    list_serializer_class = EventListSerializer
    filterset_class = EventFilter
    search_fields = ["title", "summary", "content", "venue"]
    ordering_fields = ["display_order", "event_date", "created_at", "title"]

    @extend_schema(
        operation_id="events_upload_image",
        summary="Upload a photo to this event's gallery",
        description=(
            "Multipart upload. Set `is_featured=true` to make the photo the event's "
            "highlight image - the previously featured photo is demoted automatically."
        ),
        request={"multipart/form-data": EventImageSerializer},
        responses={201: EventImageSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="images",
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def upload_image(self, request, **kwargs):
        """Attach an image to this event without the caller resolving its id."""
        event = self.get_object()
        data = request.data.copy()
        data["event"] = event.slug

        serializer = EventImageSerializer(data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EventImageViewSet(viewsets.ModelViewSet):
    """Direct CRUD over event gallery photos."""

    queryset = EventImage.objects.select_related("event").all()
    serializer_class = EventImageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["event__slug", "is_featured"]
    ordering_fields = ["display_order", "created_at"]
    ordering = ["display_order", "id"]

    @extend_schema(summary="Make this photo the event's featured image", responses={200: EventImageSerializer})
    @action(detail=True, methods=["post"], url_path="set-featured")
    def set_featured(self, request, pk=None):
        image = self.get_object()
        image.is_featured = True
        image.save()  # demotes the previous featured photo inside a transaction
        return Response(self.get_serializer(image).data)
