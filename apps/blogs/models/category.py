"""Blog categories."""

from apps.core.models import NamedTaxonomy


class BlogCategory(NamedTaxonomy):
    """
    Topic bucket for blog posts - "Research", "Campus Life", "Placements", ...

    Separate from :class:`~apps.events.models.EventCategory` on purpose: blogs
    and events are browsed independently and their category lists should be
    free to diverge.
    """

    class Meta(NamedTaxonomy.Meta):
        abstract = False
        verbose_name = "Blog Category"
        verbose_name_plural = "Blog Categories"
