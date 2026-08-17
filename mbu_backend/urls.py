"""
Root URL configuration.

Layout:
    /admin/         Unfold-powered admin dashboard
    /ckeditor/      CKEditor image upload & browse endpoints (staff only)
    /api/v1/        Versioned REST API consumed by the website and the MCP server
    /api/docs/      Swagger UI
    /api/redoc/     ReDoc
    /api/schema/    Raw OpenAPI schema
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

api_v1_patterns = [
    path("", include("apps.core.api.urls")),
    path("", include("apps.events.api.urls")),
    path("", include("apps.blogs.api.urls")),
    path("", include("apps.faculty.api.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("api/v1/", include((api_v1_patterns, "api"), namespace="v1")),
    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Token endpoint used by the MCP server setup flow
    path("api/auth/", include("rest_framework.urls")),
]

# In development Django serves uploaded media itself; behind a real web server
# (nginx, S3, ...) this is handled upstream and these routes are inert.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
