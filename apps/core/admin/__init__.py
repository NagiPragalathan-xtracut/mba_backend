"""Core admin registrations.

Split by concern: `mixins` holds the reusable pieces, `dashboard` builds the
admin landing page, and one module per registered model.
"""

from .course import CourseAdmin
from .department import DepartmentAdmin

# Imported for the side effect of re-registering Django's and DRF's admins
# with Unfold styling.
from . import third_party  # noqa: F401  isort:skip

__all__ = ["CourseAdmin", "DepartmentAdmin", "third_party"]
