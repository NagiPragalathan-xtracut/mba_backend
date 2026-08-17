"""Event serializers."""

from rest_framework import serializers

from apps.core.api.serializers import (
    DepartmentBriefSerializer,
    SEOModelSerializerMixin,
    TaxonomySerializer,
    WritableSlugRelatedField,
)
from apps.core.models import Department
from apps.events.models import Event, EventCategory, EventImage


class EventCategorySerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = EventCategory


class EventImageSerializer(serializers.ModelSerializer):
    """A photo in an event gallery.

    Writes accept the parent event by slug (or id/UUID), so a client never has
    to resolve a numeric primary key before uploading.
    """

    event = WritableSlugRelatedField(slug_field="slug", queryset=Event.objects.all())
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = EventImage
        fields = [
            "id", "unique_id", "event", "image", "image_url",
            "alt", "caption", "is_featured", "display_order", "created_at",
        ]
        read_only_fields = ["id", "unique_id", "created_at"]
        extra_kwargs = {"image": {"write_only": True}}

    def get_image_url(self, obj) -> str:
        request = self.context.get("request")
        if not obj.image:
            return ""
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class EventImageBriefSerializer(serializers.ModelSerializer):
    """Read-only gallery entry nested inside an event payload."""

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = EventImage
        fields = ["id", "unique_id", "image_url", "alt", "caption", "is_featured", "display_order"]

    def get_image_url(self, obj) -> str:
        request = self.context.get("request")
        if not obj.image:
            return ""
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class EventListSerializer(serializers.ModelSerializer):
    """Compact shape for listing pages - no rich text body, no full gallery."""

    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    departments = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    featured_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "unique_id", "title", "slug", "summary",
            "category", "category_name", "departments",
            "event_date", "end_date", "venue",
            "featured_image_url", "is_published", "is_featured", "display_order",
            "created_at", "updated_at",
        ]

    def get_featured_image_url(self, obj) -> str:
        request = self.context.get("request")
        url = obj.featured_image_url
        if not url:
            return ""
        return request.build_absolute_uri(url) if request else url


class EventSerializer(SEOModelSerializerMixin, serializers.ModelSerializer):
    """Full read/write representation of an event."""

    category = WritableSlugRelatedField(slug_field="slug", queryset=EventCategory.objects.all())
    departments = WritableSlugRelatedField(
        slug_field="slug", many=True, queryset=Department.objects.all(), required=False,
    )
    category_detail = EventCategorySerializer(source="category", read_only=True)
    departments_detail = DepartmentBriefSerializer(source="departments", many=True, read_only=True)
    images = EventImageBriefSerializer(many=True, read_only=True)
    featured_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "unique_id", "title", "slug", "summary", "content",
            "category", "category_detail", "departments", "departments_detail",
            "event_date", "end_date", "venue",
            "images", "featured_image_url",
            "is_published", "is_featured", "display_order",
            "created_at", "updated_at",
            # SEO fields stay writable so an editor can override the generated
            # values through the API as well as the admin.
            "meta_title", "meta_description", "keywords", "canonical_url", "robots", "author",
            "og_title", "og_description", "og_image",
            "twitter_card", "twitter_title", "twitter_description", "twitter_image",
            "schema_json",
        ]
        read_only_fields = ["id", "unique_id", "created_at", "updated_at"]
        extra_kwargs = {
            "slug": {"required": False},
            # Every SEO field is optional on write - blanks are auto-generated.
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

    def validate(self, attrs):
        start = attrs.get("event_date", getattr(self.instance, "event_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than the event date."})
        return attrs
