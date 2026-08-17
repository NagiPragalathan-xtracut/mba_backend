"""Faculty designations."""

from apps.core.models import NamedTaxonomy


class Designation(NamedTaxonomy):
    """
    A job title - "Professor", "Associate Professor", "Head of Department", ...

    Stored as a table so titles stay consistent across every profile and can be
    ordered by seniority via ``display_order``.
    """

    class Meta(NamedTaxonomy.Meta):
        abstract = False
        verbose_name = "Designation"
        verbose_name_plural = "Designations"
