"""Serializer building blocks shared by the content apps."""

from rest_framework import serializers

from apps.core.models import Course, Department


class SEOSerializer(serializers.Serializer):
    """
    Read-only view of the SEO field set.

    Nested under each content object as `seo` so the frontend can render every
    meta tag from one object instead of picking fields off the root payload.
    """

    meta_title = serializers.CharField(read_only=True)
    meta_description = serializers.CharField(read_only=True)
    keywords = serializers.CharField(read_only=True)
    canonical_url = serializers.CharField(read_only=True)
    robots = serializers.CharField(read_only=True)
    author = serializers.CharField(read_only=True)
    og_title = serializers.CharField(read_only=True)
    og_description = serializers.CharField(read_only=True)
    og_image = serializers.CharField(read_only=True)
    twitter_card = serializers.CharField(read_only=True)
    twitter_title = serializers.CharField(read_only=True)
    twitter_description = serializers.CharField(read_only=True)
    twitter_image = serializers.CharField(read_only=True)
    schema_json = serializers.JSONField(read_only=True)


class SEOModelSerializerMixin:
    """
    SEO support for a content ModelSerializer.

    Exposes the whole SEO field set as a nested, read-only `seo` object, and
    refreshes the relation-dependent SEO values (keywords, schema.org
    affiliations) once DRF has written the many-to-many fields - which it does
    *after* creating the row.
    """

    def get_fields(self):
        fields = super().get_fields()
        fields["seo"] = SEOSerializer(source="*", read_only=True)
        return fields

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.sync_related_seo()
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.sync_related_seo()
        return instance


class TaxonomySerializer(serializers.ModelSerializer):
    """Shared shape for every simple lookup table."""

    class Meta:
        fields = ["id", "unique_id", "name", "slug", "description", "display_order", "is_active"]
        read_only_fields = ["id", "unique_id"]
        extra_kwargs = {"slug": {"required": False}}


class DepartmentSerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = Department
        fields = TaxonomySerializer.Meta.fields + ["short_name"]


class CourseSerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = Course
        fields = TaxonomySerializer.Meta.fields + ["short_name"]


class CourseBriefSerializer(serializers.ModelSerializer):
    """Compact course representation for nesting inside content payloads."""

    class Meta:
        model = Course
        fields = ["id", "name", "slug", "short_name"]


class DepartmentBriefSerializer(serializers.ModelSerializer):
    """Compact department representation for nesting inside content payloads."""

    class Meta:
        model = Department
        fields = ["id", "name", "slug", "short_name"]


class WritableSlugRelatedField(serializers.SlugRelatedField):
    """
    Slug-addressable relation with a clearer error message.

    Lets API clients (notably the MCP server) write
    ``{"departments": ["cse", "ece"]}`` instead of hunting for numeric ids.
    """

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            model_name = self.get_queryset().model._meta.verbose_name
            raise serializers.ValidationError(
                f"No {model_name} exists with slug '{data}'. "
                f"Create it first, or pass one of the existing slugs."
            )
