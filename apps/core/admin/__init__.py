"""Core admin registrations.

Split by concern: `mixins` holds the reusable pieces, `dashboard` builds the
admin landing page, and one module per registered model.
"""

from .department import DepartmentAdmin

__all__ = ["DepartmentAdmin"]
