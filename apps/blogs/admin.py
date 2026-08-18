"""Admin for blog posts."""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.blogs.models import Blog, BlogCategory, BlogImage
from apps.core.admin.mixins import (
    AUDIT_FIELDS,
    AUDIT_FIELDSET,
    SEO_FIELDSETS,
    ContentAdminMixin,
    PublishActionsMixin,
    image_preview_html,
)


class BlogImageInline(TabularInline):
    """Repeatable in-article image rows. Click "+" to add another."""

    model = BlogImage
    extra = 1
    fields = ["preview", "image", "alt", "caption", "display_order"]
    readonly_fields = ["preview"]
    ordering = ["display_order", "id"]
    tab = True

    @display(description="Preview")
    def preview(self, obj):
        return image_preview_html(obj.image)


@admin.register(BlogCategory)
class BlogCategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "blog_count", "display_order", "status_badge"]
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

    @display(description="Posts")
    def blog_count(self, obj):
        return obj.blogs.count()

    @display(description="Status", label={"Active": "success", "Hidden": "danger"})
    def status_badge(self, obj):
        return "Active" if obj.is_active else "Hidden"


@admin.register(Blog)
class BlogAdmin(ContentAdminMixin, PublishActionsMixin, ModelAdmin):
    list_display = ["thumbnail", "title", "category_list", "author_name", "published_date", "display_order", "status_badge"]
    list_display_links = ["thumbnail", "title"]
    list_editable = ["display_order"]
    list_filter = ["categories", "departments", "courses", "is_published", "is_featured", "published_date"]
    list_filter_submit = True
    search_fields = ["title", "summary", "content", "author_name"]
    autocomplete_fields = ["categories", "departments", "courses"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = AUDIT_FIELDS
    date_hierarchy = "published_date"
    list_per_page = 25
    inlines = [BlogImageInline]
    compressed_fields = True
    warn_unsaved_form = True
    save_on_top = True

    fieldsets = (
        (
            "Post",
            {
                "classes": ["tab"],
                "fields": ("title", "slug", "categories", "departments", "courses", "summary", "content"),
            },
        ),
        (
            "Cover & Byline",
            {
                "classes": ["tab"],
                "description": "The cover image is used on listing cards and as the social share image.",
                "fields": ("featured_image", "featured_image_alt", "author_name", "published_date"),
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
        return super().get_queryset(request).prefetch_related("categories", "departments", "courses")

    @display(description="")
    def thumbnail(self, obj):
        return image_preview_html(obj.featured_image, height=44)

    @display(description="Categories")
    def category_list(self, obj):
        names = [category.name for category in obj.categories.all()]
        return ", ".join(names) if names else "—"

    @display(
        description="Status",
        label={"Published": "success", "Featured": "info", "Draft": "danger"},
    )
    def status_badge(self, obj):
        if not obj.is_published:
            return "Draft"
        return "Featured" if obj.is_featured else "Published"
