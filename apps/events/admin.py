"""Admin for events.

The gallery is an inline on the event form: photos are uploaded in place and
the highlight image is chosen with the `is_featured` checkbox, so an editor
never leaves the page or uploads the same file twice.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.core.admin.mixins import (
    AUDIT_FIELDS,
    AUDIT_FIELDSET,
    SEO_FIELDSETS,
    ContentAdminMixin,
    PublishActionsMixin,
    image_preview_html,
)
from apps.events.models import Event, EventCategory, EventImage


class EventImageInline(TabularInline):
    """Repeatable photo rows. Click "+" to add another."""

    model = EventImage
    extra = 1
    fields = ["preview", "image", "alt", "caption", "is_featured", "display_order"]
    readonly_fields = ["preview"]
    ordering = ["display_order", "id"]
    tab = True

    @display(description="Preview")
    def preview(self, obj):
        return image_preview_html(obj.image)


@admin.register(EventCategory)
class EventCategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "event_count", "display_order", "status_badge"]
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

    @display(description="Events")
    def event_count(self, obj):
        return obj.events.count()

    @display(description="Status", label={"Active": "success", "Hidden": "danger"})
    def status_badge(self, obj):
        return "Active" if obj.is_active else "Hidden"


@admin.register(Event)
class EventAdmin(ContentAdminMixin, PublishActionsMixin, ModelAdmin):
    list_display = ["thumbnail", "title", "category", "department_list", "event_date", "timing", "display_order", "status_badge"]
    list_display_links = ["thumbnail", "title"]
    list_editable = ["display_order"]
    list_filter = ["category", "departments", "courses", "is_published", "is_featured", "event_date"]
    list_filter_submit = True
    search_fields = ["title", "summary", "content", "venue"]
    autocomplete_fields = ["category", "departments", "courses"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = AUDIT_FIELDS
    date_hierarchy = "event_date"
    list_per_page = 25
    inlines = [EventImageInline]
    compressed_fields = True
    warn_unsaved_form = True
    save_on_top = True

    fieldsets = (
        (
            "Event",
            {
                "classes": ["tab"],
                "fields": ("title", "slug", "category", "departments", "courses", "summary", "content"),
            },
        ),
        (
            "Schedule & Venue",
            {
                "classes": ["tab"],
                "description": (
                    "Times are optional. Fill them in and the website shows a "
                    "'Timing' line; leave them blank for news and announcements."
                ),
                "fields": ("event_date", "end_date", "start_time", "end_time", "venue"),
            },
        ),
        (
            "Publishing",
            {
                "classes": ["tab"],
                "description": "Unpublished events are hidden from the website and the public API.",
                "fields": ("is_published", "is_featured", "display_order"),
            },
        ),
        *SEO_FIELDSETS,
        AUDIT_FIELDSET,
    )

    def get_queryset(self, request):
        # Avoids an N+1 when rendering the category / departments columns.
        return super().get_queryset(request).select_related("category").prefetch_related("departments", "courses", "images")

    @display(description="")
    def thumbnail(self, obj):
        image = obj.featured_image
        return image_preview_html(image.image if image else None, height=44)

    @display(description="Timing")
    def timing(self, obj):
        return obj.timing_label or "—"

    @display(description="Departments")
    def department_list(self, obj):
        names = [department.label for department in obj.departments.all()]
        return ", ".join(names) if names else "University-wide"

    @display(
        description="Status",
        label={"Published": "success", "Featured": "info", "Draft": "danger"},
    )
    def status_badge(self, obj):
        if not obj.is_published:
            return "Draft"
        return "Featured" if obj.is_featured else "Published"
