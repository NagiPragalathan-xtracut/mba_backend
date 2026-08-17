"""Event categories."""

from apps.core.models import NamedTaxonomy


class EventCategory(NamedTaxonomy):
    """
    How an event is classified on the website - "Upcoming", "Achievements", ...

    Kept as a table rather than a fixed choice list so the marketing team can
    add a category ("Workshops", "Convocation") without a code change. The two
    categories the site launches with are created by a data migration.
    """

    # Slugs of the categories the project ships with. Referenced by the data
    # migration and by the seeding management command.
    UPCOMING = "upcoming"
    ACHIEVEMENTS = "achievements"

    DEFAULT_CATEGORIES = (
        (UPCOMING, "Upcoming", "Events that have not happened yet."),
        (ACHIEVEMENTS, "Achievements", "Awards, milestones and recognitions already earned."),
    )

    class Meta(NamedTaxonomy.Meta):
        abstract = False
        verbose_name = "Event Category"
        verbose_name_plural = "Event Categories"
