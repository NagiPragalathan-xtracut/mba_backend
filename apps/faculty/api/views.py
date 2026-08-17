"""Faculty API endpoints."""

from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.api.viewsets import BaseContentViewSet, TaxonomyViewSet
from apps.faculty.api.filters import FacultyFilter
from apps.faculty.api.serializers import (
    DesignationSerializer,
    FacultyBannerSerializer,
    FacultyListSerializer,
    FacultySectionSerializer,
    FacultySerializer,
)
from apps.faculty.models import Designation, Faculty, FacultyBanner, FacultySection


class DesignationViewSet(TaxonomyViewSet):
    """Job titles used across faculty profiles."""

    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    filterset_fields = ["is_active"]


@extend_schema_view(
    list=extend_schema(summary="List faculty", description="Public directory. Filter by department, designation or qualification."),
    retrieve=extend_schema(summary="Retrieve one faculty profile by slug, id or UUID"),
    create=extend_schema(summary="Create a faculty profile (requires a token)"),
)
class FacultyViewSet(BaseContentViewSet):
    """Faculty profiles."""

    queryset = (
        Faculty.objects.select_related("designation")
        .prefetch_related("departments", "sections", "banners")
        .all()
    )
    serializer_class = FacultySerializer
    list_serializer_class = FacultyListSerializer
    filterset_class = FacultyFilter
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ["name", "qualification", "mail_id", "sections__heading", "sections__content"]
    ordering_fields = ["display_order", "name", "created_at"]
    ordering = ["display_order", "name"]

    @extend_schema(
        # Explicit id: this action shares a path name with FacultySectionViewSet,
        # which would otherwise collide in the generated OpenAPI schema.
        operation_id="faculty_add_section",
        summary="Add a profile section",
        description='Appends a "heading + rich text" block, the API equivalent of the admin "+" button.',
        request=FacultySectionSerializer,
        responses={201: FacultySectionSerializer},
    )
    @action(detail=True, methods=["post"], url_path="sections")
    def add_section(self, request, **kwargs):
        faculty = self.get_object()
        data = request.data.copy()
        data["faculty"] = faculty.slug

        serializer = FacultySectionSerializer(data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="faculty_upload_banner",
        summary="Upload a banner image for this profile",
        request={"multipart/form-data": FacultyBannerSerializer},
        responses={201: FacultyBannerSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="banners",
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def upload_banner(self, request, **kwargs):
        faculty = self.get_object()
        data = request.data.copy()
        data["faculty"] = faculty.slug

        serializer = FacultyBannerSerializer(data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FacultySectionViewSet(viewsets.ModelViewSet):
    """Direct CRUD over profile sections."""

    queryset = FacultySection.objects.select_related("faculty").all()
    serializer_class = FacultySectionSerializer
    filterset_fields = ["faculty__slug", "is_visible"]
    ordering_fields = ["display_order", "created_at"]
    ordering = ["display_order", "id"]


class FacultyBannerViewSet(viewsets.ModelViewSet):
    """Direct CRUD over profile banners."""

    queryset = FacultyBanner.objects.select_related("faculty").all()
    serializer_class = FacultyBannerSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["faculty__slug"]
    ordering_fields = ["display_order", "created_at"]
    ordering = ["display_order", "id"]
