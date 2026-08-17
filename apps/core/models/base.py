"""Abstract model bases shared by every app."""

import uuid

from django.db import models


class PublishedQuerySet(models.QuerySet):
    """Reusable filters for anything that can be published or featured."""

    def published(self):
        return self.filter(is_published=True)

    def featured(self):
        return self.filter(is_published=True, is_featured=True)

    def in_display_order(self):
        """Editor-defined order first, newest first within the same rank.

        Deliberately not named ``ordered`` - that is an existing ``QuerySet``
        property Django itself reads when deciding whether pagination is safe.
        """
        return self.order_by("display_order", "-created_at")


class TimeStampedModel(models.Model):
    """
    Adds an external identifier and audit timestamps.

    ``unique_id`` is what external clients (the MCP server, the public website)
    should reference: it is stable across database dumps and does not leak how
    many rows exist, unlike a sequential primary key.
    """

    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrderedModel(TimeStampedModel):
    """Timestamped rows carrying a manual ``display_order``."""

    display_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Lower numbers appear first. Ties fall back to newest-first.",
    )

    class Meta:
        abstract = True


class NamedTaxonomy(TimeStampedModel):
    """
    Base for simple lookup tables (categories, designations, departments).

    Keeps the shape identical everywhere: a unique name, an auto-filled slug,
    an optional description and a manual ordering weight.
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="Auto-generated from the name when left blank.")
    description = models.TextField(blank=True, default="")
    display_order = models.PositiveIntegerField(default=0, db_index=True, help_text="Lower numbers appear first.")
    is_active = models.BooleanField(default=True, help_text="Inactive entries are hidden from the public API.")

    class Meta:
        abstract = True
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            # Imported here to avoid a circular import at module load time.
            from apps.core.utils import unique_slugify

            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)
