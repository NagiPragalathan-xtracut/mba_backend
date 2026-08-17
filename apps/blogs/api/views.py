"""Blog API endpoints."""

from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.blogs.api.filters import BlogFilter
from apps.blogs.api.serializers import (
    BlogCategorySerializer,
    BlogImageSerializer,
    BlogListSerializer,
    BlogSerializer,
)
from apps.blogs.models import Blog, BlogCategory, BlogImage
from apps.core.api.viewsets import BaseContentViewSet, TaxonomyViewSet


class BlogCategoryViewSet(TaxonomyViewSet):
    """Blog topic categories."""

    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    filterset_fields = ["is_active"]


@extend_schema_view(
    list=extend_schema(summary="List blog posts", description="Public listing. Filter by category, department, author or date."),
    retrieve=extend_schema(summary="Retrieve one blog post by slug, id or UUID"),
    create=extend_schema(summary="Create a blog post (requires a token)"),
)
class BlogViewSet(BaseContentViewSet):
    """Blog posts."""

    queryset = Blog.objects.prefetch_related("categories", "departments", "images").all()
    serializer_class = BlogSerializer
    list_serializer_class = BlogListSerializer
    filterset_class = BlogFilter
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ["title", "summary", "content", "author_name"]
    ordering_fields = ["display_order", "published_date", "created_at", "title"]
    ordering = ["display_order", "-published_date"]

    @extend_schema(
        operation_id="blogs_upload_image",
        summary="Upload a photo to this post's gallery",
        request={"multipart/form-data": BlogImageSerializer},
        responses={201: BlogImageSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="images",
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def upload_image(self, request, **kwargs):
        blog = self.get_object()
        data = request.data.copy()
        data["blog"] = blog.slug

        serializer = BlogImageSerializer(data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BlogImageViewSet(viewsets.ModelViewSet):
    """Direct CRUD over blog gallery photos."""

    queryset = BlogImage.objects.select_related("blog").all()
    serializer_class = BlogImageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["blog__slug"]
    ordering_fields = ["display_order", "created_at"]
    ordering = ["display_order", "id"]
