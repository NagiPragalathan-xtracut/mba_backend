"""Blog serializers."""

from rest_framework import serializers

from apps.blogs.models import Blog, BlogCategory, BlogImage
from apps.core.api.serializers import (
    DepartmentBriefSerializer,
    SEOModelSerializerMixin,
    TaxonomySerializer,
    WritableSlugRelatedField,
)
from apps.core.models import Department


class BlogCategorySerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = BlogCategory


class BlogImageSerializer(serializers.ModelSerializer):
    """A photo in a blog gallery; the parent blog is addressed by slug."""

    blog = WritableSlugRelatedField(slug_field="slug", queryset=Blog.objects.all())
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BlogImage
        fields = [
            "id", "unique_id", "blog", "image", "image_url",
            "alt", "caption", "display_order", "created_at",
        ]
        read_only_fields = ["id", "unique_id", "created_at"]
        extra_kwargs = {"image": {"write_only": True}}

    def get_image_url(self, obj) -> str:
        request = self.context.get("request")
        if not obj.image:
            return ""
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class BlogImageBriefSerializer(serializers.ModelSerializer):
    """Read-only gallery entry nested inside a blog payload."""

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BlogImage
        fields = ["id", "unique_id", "image_url", "alt", "caption", "display_order"]

    def get_image_url(self, obj) -> str:
        request = self.context.get("request")
        if not obj.image:
            return ""
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class BlogListSerializer(serializers.ModelSerializer):
    """Compact shape for listing pages."""

    categories = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    departments = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    reading_time_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Blog
        fields = [
            "id", "unique_id", "title", "slug", "summary",
            "categories", "departments", "author_name", "published_date",
            "featured_image_url", "reading_time_minutes",
            "is_published", "is_featured", "display_order",
            "created_at", "updated_at",
        ]

    def get_featured_image_url(self, obj) -> str:
        request = self.context.get("request")
        url = obj.featured_image_url
        if not url:
            return ""
        return request.build_absolute_uri(url) if request else url


class BlogSerializer(SEOModelSerializerMixin, serializers.ModelSerializer):
    """Full read/write representation of a blog post."""

    categories = WritableSlugRelatedField(
        slug_field="slug", many=True, queryset=BlogCategory.objects.all(), required=False,
    )
    departments = WritableSlugRelatedField(
        slug_field="slug", many=True, queryset=Department.objects.all(), required=False,
    )
    categories_detail = BlogCategorySerializer(source="categories", many=True, read_only=True)
    departments_detail = DepartmentBriefSerializer(source="departments", many=True, read_only=True)
    images = BlogImageBriefSerializer(many=True, read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    reading_time_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Blog
        fields = [
            "id", "unique_id", "title", "slug", "summary", "content",
            "categories", "categories_detail", "departments", "departments_detail",
            "featured_image", "featured_image_url", "featured_image_alt",
            "author_name", "published_date", "reading_time_minutes",
            "images",
            "is_published", "is_featured", "display_order",
            "created_at", "updated_at",
            "meta_title", "meta_description", "keywords", "canonical_url", "robots", "author",
            "og_title", "og_description", "og_image",
            "twitter_card", "twitter_title", "twitter_description", "twitter_image",
            "schema_json",
        ]
        read_only_fields = ["id", "unique_id", "created_at", "updated_at"]
        extra_kwargs = {
            "slug": {"required": False},
            "featured_image": {"write_only": True, "required": False},
            **{
                field: {"required": False}
                for field in (
                    "meta_title", "meta_description", "keywords", "canonical_url", "author",
                    "og_title", "og_description", "og_image",
                    "twitter_title", "twitter_description", "twitter_image", "schema_json",
                )
            },
        }

    def get_featured_image_url(self, obj) -> str:
        request = self.context.get("request")
        url = obj.featured_image_url
        if not url:
            return ""
        return request.build_absolute_uri(url) if request else url
