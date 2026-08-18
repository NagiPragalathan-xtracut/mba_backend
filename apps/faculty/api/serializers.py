"""Faculty serializers."""

from rest_framework import serializers

from apps.core.api.serializers import (
    DepartmentBriefSerializer,
    SEOModelSerializerMixin,
    TaxonomySerializer,
    WritableSlugRelatedField,
)
from apps.core.models import Department
from apps.faculty.models import Designation, Faculty, FacultyBanner, FacultySection


class DesignationSerializer(TaxonomySerializer):
    class Meta(TaxonomySerializer.Meta):
        model = Designation


class FacultySectionSerializer(serializers.ModelSerializer):
    """
    One "heading + rich text" block on a profile.

    This is the repeatable set an editor grows with the "+" button in the
    admin; over the API it is a normal nested resource.
    """

    faculty = WritableSlugRelatedField(slug_field="slug", queryset=Faculty.objects.all())

    class Meta:
        model = FacultySection
        fields = ["id", "unique_id", "faculty", "heading", "content", "display_order", "is_visible", "created_at"]
        read_only_fields = ["id", "unique_id", "created_at"]


class FacultySectionBriefSerializer(serializers.ModelSerializer):
    """Read-only section nested inside a faculty payload."""

    class Meta:
        model = FacultySection
        fields = ["id", "unique_id", "heading", "content", "display_order", "is_visible"]


class FacultyBannerSerializer(serializers.ModelSerializer):
    faculty = WritableSlugRelatedField(slug_field="slug", queryset=Faculty.objects.all())
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = FacultyBanner
        fields = ["id", "unique_id", "faculty", "image", "image_url", "alt", "display_order", "created_at"]
        read_only_fields = ["id", "unique_id", "created_at"]
        extra_kwargs = {"image": {"write_only": True}}

    def get_image_url(self, obj) -> str:
        request = self.context.get("request")
        if not obj.image:
            return ""
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class FacultyBannerBriefSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = FacultyBanner
        fields = ["id", "unique_id", "image_url", "alt", "display_order"]

    def get_image_url(self, obj) -> str:
        request = self.context.get("request")
        if not obj.image:
            return ""
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class FacultyListSerializer(serializers.ModelSerializer):
    """Compact shape for the faculty directory."""

    designation = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    designation_name = serializers.CharField(source="designation.name", read_only=True)
    departments = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = [
            "id", "unique_id", "name", "slug",
            "designation", "designation_name", "departments",
            "qualification", "mail_id", "phone_number",
            "image_url", "image_alt", "external_image_url",
            "is_published", "is_featured", "display_order",
            "created_at", "updated_at",
        ]

    def get_image_url(self, obj) -> str:
        request = self.context.get("request")
        url = obj.image_url
        if not url:
            return ""
        return request.build_absolute_uri(url) if request else url


class FacultySerializer(SEOModelSerializerMixin, serializers.ModelSerializer):
    """Full read/write representation of a faculty profile."""

    designation = WritableSlugRelatedField(slug_field="slug", queryset=Designation.objects.all())
    departments = WritableSlugRelatedField(
        slug_field="slug", many=True, queryset=Department.objects.all(), required=False,
    )
    designation_detail = DesignationSerializer(source="designation", read_only=True)
    departments_detail = DepartmentBriefSerializer(source="departments", many=True, read_only=True)
    sections = FacultySectionBriefSerializer(many=True, read_only=True)
    banners = FacultyBannerBriefSerializer(many=True, read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = [
            "id", "unique_id", "name", "slug",
            "designation", "designation_detail", "departments", "departments_detail",
            "qualification", "mail_id", "phone_number", "profile_link",
            "image", "image_url", "image_alt", "external_image_url",
            "sections", "banners",
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
            "image": {"write_only": True, "required": False},
            **{
                field: {"required": False}
                for field in (
                    "meta_title", "meta_description", "keywords", "canonical_url", "author",
                    "og_title", "og_description", "og_image",
                    "twitter_title", "twitter_description", "twitter_image", "schema_json",
                )
            },
        }

    def get_image_url(self, obj) -> str:
        request = self.context.get("request")
        url = obj.image_url
        if not url:
            return ""
        return request.build_absolute_uri(url) if request else url
