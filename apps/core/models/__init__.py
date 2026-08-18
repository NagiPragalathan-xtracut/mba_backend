"""Core models.

Models are split by concern into one module each and re-exported here so the
rest of the project can simply `from apps.core.models import Department`.
"""

from .base import NamedTaxonomy, OrderedModel, PublishedQuerySet, TimeStampedModel
from .content import ContentBase, ContentQuerySet
from .course import Course
from .department import Department
from .seo import SEOMixin

__all__ = [
    "TimeStampedModel",
    "OrderedModel",
    "NamedTaxonomy",
    "PublishedQuerySet",
    "SEOMixin",
    "ContentBase",
    "ContentQuerySet",
    "Department",
    "Course",
]
