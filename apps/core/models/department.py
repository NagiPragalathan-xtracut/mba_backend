"""
Departments - the taxonomy shared by events, blogs and faculty.

A single table keeps "Computer Science & Engineering" spelled one way across
every app, and lets the website filter all three content types by the same
department slug.
"""

from django.db import models

from apps.core.models.base import NamedTaxonomy


class DepartmentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Department(NamedTaxonomy):
    """An academic department or school."""

    short_name = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Abbreviation shown in compact UI, e.g. 'CSE'.",
    )

    objects = DepartmentQuerySet.as_manager()

    class Meta(NamedTaxonomy.Meta):
        abstract = False
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    @property
    def label(self) -> str:
        """Short name when available, otherwise the full name."""
        return self.short_name or self.name
