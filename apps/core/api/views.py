"""Core API endpoints: departments and a health probe."""

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.api.serializers import DepartmentSerializer
from apps.core.api.viewsets import TaxonomyViewSet
from apps.core.models import Department


class DepartmentViewSet(TaxonomyViewSet):
    """
    Academic departments.

    Shared by events, blogs and faculty - create a department here once and
    reference it by slug from any of them.
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "short_name", "description"]


@extend_schema(
    summary="Service health check",
    description="Reports API availability and database connectivity. Used by the MCP server on startup.",
    responses={200: dict, 503: dict},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Confirm the API is up and can reach its database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 - report any driver failure verbatim
        return Response(
            {"status": "unhealthy", "database": "unreachable", "detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "status": "healthy",
            "database": "connected",
            "authenticated": request.user.is_authenticated,
            "user": request.user.get_username() if request.user.is_authenticated else None,
        }
    )
