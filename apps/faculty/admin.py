"""
Admin for faculty profiles.

The profile body is built from `FacultySection` inlines - an editor clicks "+"
to add another "heading + rich text" block, exactly as the brief asked, instead
of being limited to a fixed set of columns.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import display

from apps.core.admin.mixins import (
    AUDIT_FIELDS,
    AUDIT_FIELDSET,
    SEO_FIELDSETS,
    ContentAdminMixin,
    PublishActionsMixin,
    image_preview_html,
)
from apps.faculty.models import Designation, Faculty, FacultyBanner, FacultySection


class FacultySectionInline(StackedInline):
    """
    Repeatable profile sections.

    Stacked rather than tabular because each row contains a full rich-text
    editor, which needs the width.
    """

    model = FacultySection
    extra = 1
    fields = ["heading", "content", "display_order", "is_visible"]
    ordering = ["display_order", "id"]
    verbose_name = "Profile Section"
    verbose_name_plural = "Profile Sections (click + to add another)"
    tab = True


class FacultyBannerInline(TabularInline):
    """Repeatable banner images."""

    model = FacultyBanner
    extra = 1
    fields = ["preview", "image", "alt", "display_order"]
    readonly_fields = ["preview"]
    ordering = ["display_order", "id"]
    tab = True

    @display(description="Preview")
    def preview(self, obj):
        return image_preview_html(obj.image)


@admin.register(Designation)
class DesignationAdmin(ModelAdmin):
    list_display = ["name", "slug", "faculty_count", "display_order", "status_badge"]
    list_editable = ["display_order"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = AUDIT_FIELDS
    compressed_fields = True

    fieldsets = (
        (None, {"fields": ("name", "slug", "description")}),
        ("Display", {"fields": ("display_order", "is_active")}),
        ("Record", {"classes": ["collapse"], "fields": AUDIT_FIELDS}),
    )

    @display(description="Faculty")
    def faculty_count(self, obj):
        return obj.faculty_members.count()

    @display(description="Status", label={"Active": "success", "Hidden": "danger"})
    def status_badge(self, obj):
        return "Active" if obj.is_active else "Hidden"


@admin.register(Faculty)
class FacultyAdmin(ContentAdminMixin, PublishActionsMixin, ModelAdmin):
    list_display = ["photo", "name", "designation", "department_list", "section_count", "display_order", "status_badge"]
    list_display_links = ["photo", "name"]
    list_editable = ["display_order"]
    list_filter = ["designation", "departments", "is_published", "is_featured"]
    list_filter_submit = True
    search_fields = ["name", "qualification", "mail_id", "phone_number"]
    autocomplete_fields = ["designation", "departments"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = AUDIT_FIELDS
    list_per_page = 25
    inlines = [FacultySectionInline, FacultyBannerInline]
    compressed_fields = True
    warn_unsaved_form = True
    save_on_top = True

    fieldsets = (
        (
            "Profile",
            {
                "classes": ["tab"],
                "fields": ("name", "slug", "designation", "departments", "qualification"),
            },
        ),
        (
            "Photo",
            {
                "classes": ["tab"],
                "description": (
                    "Upload a file, or point at an existing photo on the university CDN. "
                    "An uploaded file always wins when both are filled in."
                ),
                "fields": ("image", "external_image_url", "image_alt"),
            },
        ),
        (
            "Contact",
            {
                "classes": ["tab"],
                "description": "All contact details are optional and are shown publicly when filled.",
                "fields": ("mail_id", "phone_number", "profile_link"),
            },
        ),
        (
            "Publishing",
            {
                "classes": ["tab"],
                "fields": ("is_published", "is_featured", "display_order"),
            },
        ),
        *SEO_FIELDSETS,
        AUDIT_FIELDSET,
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("designation").prefetch_related("departments", "sections")

    @display(description="")
    def photo(self, obj):
        return image_preview_html(obj.image, height=44)

    @display(description="Departments")
    def department_list(self, obj):
        names = [department.label for department in obj.departments.all()]
        return ", ".join(names) if names else "—"

    @display(description="Sections")
    def section_count(self, obj):
        return obj.sections.count()

    @display(
        description="Status",
        label={"Published": "success", "Featured": "info", "Draft": "danger"},
    )
    def status_badge(self, obj):
        if not obj.is_published:
            return "Draft"
        return "Featured" if obj.is_featured else "Published"
