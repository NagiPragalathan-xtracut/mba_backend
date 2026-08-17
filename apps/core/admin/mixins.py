"""
Admin building blocks shared by every content app.

Keeps the three content admins visually and behaviourally identical: the same
image thumbnails, the same SEO tab, the same publish/unpublish actions.
"""

from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

# Fieldsets every SEO-aware model gets appended to its own fieldsets. Rendered
# as separate tabs by Unfold thanks to the `tab` class.
SEO_FIELDSETS = (
    (
        "Search Engine",
        {
            "classes": ["tab"],
            "description": "Leave blank to auto-generate from the content when saving.",
            "fields": ("meta_title", "meta_description", "keywords", "canonical_url", "robots", "author"),
        },
    ),
    (
        "Social Sharing",
        {
            "classes": ["tab"],
            "description": "Controls how the page looks when shared on WhatsApp, LinkedIn, Facebook or X.",
            "fields": (
                "og_title", "og_description", "og_image",
                "twitter_card", "twitter_title", "twitter_description", "twitter_image",
            ),
        },
    ),
    (
        "Structured Data",
        {
            "classes": ["tab", "collapse"],
            "description": "schema.org JSON-LD. Generated automatically - only edit if you know what you are doing.",
            "fields": ("schema_json",),
        },
    ),
)

# Fields the system maintains; shown read-only so editors can see them but not
# accidentally desynchronise them.
AUDIT_FIELDS = ("unique_id", "created_at", "updated_at")

AUDIT_FIELDSET = (
    "Record",
    {
        "classes": ["tab", "collapse"],
        "fields": AUDIT_FIELDS,
    },
)


def image_preview_html(image_field, height: int = 60) -> SafeString:
    """Render a small thumbnail for an image field, or a dash when empty."""
    if not image_field:
        return mark_safe('<span class="text-slate-400">&mdash;</span>')
    return format_html(
        '<img src="{}" style="height:{}px;width:auto;border-radius:6px;'
        'object-fit:cover;border:1px solid rgba(0,0,0,.08);" loading="lazy" />',
        image_field.url,
        height,
    )


class ContentAdminMixin:
    """
    Behaviour every content admin needs.

    The admin saves the object first and its many-to-many fields second, so
    SEO values derived from departments or categories are only computable in
    `save_related`.
    """

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.sync_related_seo()


class PublishActionsMixin:
    """Bulk publish / unpublish / feature actions for content changelists."""

    actions = ["action_publish", "action_unpublish", "action_feature", "action_unfeature"]

    def _apply(self, request, queryset, verb: str, **updates):
        updated = queryset.update(**updates)
        self.message_user(request, f"{updated} item(s) {verb}.", messages.SUCCESS)

    @admin.action(description="Publish selected")
    def action_publish(self, request, queryset):
        self._apply(request, queryset, "published", is_published=True)

    @admin.action(description="Unpublish selected")
    def action_unpublish(self, request, queryset):
        self._apply(request, queryset, "unpublished", is_published=False)

    @admin.action(description="Mark as featured")
    def action_feature(self, request, queryset):
        self._apply(request, queryset, "marked as featured", is_featured=True)

    @admin.action(description="Remove from featured")
    def action_unfeature(self, request, queryset):
        self._apply(request, queryset, "removed from featured", is_featured=False)
