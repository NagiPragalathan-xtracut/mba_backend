"""
The abstract base every public content type inherits from.

`ContentBase` composes three concerns that always travel together:

* publishing state (`is_published`, `is_featured`, `display_order`)
* a unique, auto-maintained `slug`
* the full SEO field set from :class:`SEOMixin`

Its ``save()`` is the single place where slug and SEO generation are ordered
correctly (slug first, because the canonical URL is built from it).
"""

from django.db import models

from apps.core.models.base import PublishedQuerySet, TimeStampedModel
from apps.core.models.seo import SEO_MANAGED_FIELDS, SEOMixin
from apps.core.utils.slugs import unique_slugify


class ContentQuerySet(PublishedQuerySet):
    """Query helpers available on every content model."""

    def by_department(self, department_slug: str):
        return self.filter(departments__slug=department_slug).distinct()

    def by_course(self, course_slug: str):
        return self.filter(courses__slug=course_slug).distinct()


class ContentBase(SEOMixin, TimeStampedModel):
    """Publishable, sluggable, SEO-aware content."""

    #: Field the slug is derived from. Faculty overrides this with ``"name"``.
    SLUG_SOURCE_FIELD = "title"

    slug = models.SlugField(
        max_length=255, unique=True, blank=True,
        help_text="URL-friendly identifier. Generated from the title when left blank.",
    )
    is_published = models.BooleanField(
        default=True, db_index=True,
        help_text="Unpublished entries are hidden from the public API.",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Highlight this entry on listing pages.",
    )
    display_order = models.PositiveIntegerField(
        default=0, db_index=True,
        help_text="Lower numbers appear first. Ties fall back to newest-first.",
    )

    objects = ContentQuerySet.as_manager()

    class Meta:
        abstract = True

    # ------------------------------------------------------------------

    def slug_source_value(self) -> str:
        """Value the slug is generated from."""
        return str(getattr(self, self.SLUG_SOURCE_FIELD, "") or "")

    def save(self, *args, **kwargs):
        # Order matters: the canonical URL produced by generate_seo_data()
        # embeds the slug, so the slug has to exist first.
        if not self.slug:
            self.slug = unique_slugify(self, self.slug_source_value())
        self.generate_seo_data()

        # A caller passing `update_fields` lists only the columns *it* changed
        # - Django's own `update_or_create()` does exactly this. The slug and
        # SEO values we just derived are not in that list, so without this they
        # would be computed and then silently dropped before the UPDATE.
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "slug", *SEO_MANAGED_FIELDS}

        super().save(*args, **kwargs)
