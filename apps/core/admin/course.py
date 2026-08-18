"""Admin for the Course taxonomy."""

from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin.mixins import AUDIT_FIELDS
from apps.core.models import Course


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = ["name", "short_name", "slug", "usage_summary", "display_order", "status_badge"]
    list_editable = ["display_order"]
    list_filter = ["is_active"]
    search_fields = ["name", "short_name", "slug", "description"]
    ordering = ["display_order", "name"]
    readonly_fields = AUDIT_FIELDS
    prepopulated_fields = {"slug": ("name",)}
    list_per_page = 50
    compressed_fields = True
    warn_unsaved_form = True

    fieldsets = (
        (None, {"fields": ("name", "short_name", "slug", "description")}),
        (
            "Display",
            {
                "description": "Inactive courses disappear from the website's Courses filter.",
                "fields": ("display_order", "is_active"),
            },
        ),
        ("Record", {"classes": ["collapse"], "fields": AUDIT_FIELDS}),
    )

    @display(description="Status", label={"Active": "success", "Hidden": "danger"})
    def status_badge(self, obj):
        return "Active" if obj.is_active else "Hidden"

    @display(description="Used by")
    def usage_summary(self, obj):
        """How much content is tagged to this course."""
        return f"{obj.events.count()} events · {obj.blogs.count()} blogs"
