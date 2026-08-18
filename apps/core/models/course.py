"""
Courses - the programme a piece of content belongs to.

The website's News & Events sidebar offers a "Courses" filter next to the
category filter (MBA, Executive MBA, MBA (Finance), ...). Like departments,
this is a taxonomy shared by events and blogs rather than a column on each, so
"MBA (Finance)" is spelled one way everywhere and one slug filters both.
"""

from django.db import models

from apps.core.models.base import NamedTaxonomy


class CourseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Course(NamedTaxonomy):
    """A programme offered by the school."""

    short_name = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Abbreviation shown in compact UI, e.g. 'EMBA'.",
    )

    objects = CourseQuerySet.as_manager()

    class Meta(NamedTaxonomy.Meta):
        abstract = False
        verbose_name = "Course"
        verbose_name_plural = "Courses"

    @property
    def label(self) -> str:
        """Short name when available, otherwise the full name."""
        return self.short_name or self.name
