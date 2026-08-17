"""
Seed the two event categories the site launches with.

`Event.category` is a required foreign key, so without this the first event
cannot be created until someone remembers to add a category by hand. Written to
be re-runnable and reversible.
"""

from django.db import migrations
from django.utils.text import slugify

DEFAULT_CATEGORIES = (
    ("Upcoming", "Events that have not happened yet.", 10),
    ("Achievements", "Awards, milestones and recognitions already earned.", 20),
)


def create_default_categories(apps, schema_editor):
    EventCategory = apps.get_model("events", "EventCategory")
    for name, description, order in DEFAULT_CATEGORIES:
        EventCategory.objects.update_or_create(
            slug=slugify(name),
            defaults={"name": name, "description": description, "display_order": order, "is_active": True},
        )


def remove_default_categories(apps, schema_editor):
    EventCategory = apps.get_model("events", "EventCategory")
    # Only remove categories that are still unused - deleting a category that
    # events point at would fail against the PROTECT constraint anyway.
    for name, _, _ in DEFAULT_CATEGORIES:
        EventCategory.objects.filter(slug=slugify(name), events__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [("events", "0001_initial")]

    operations = [
        migrations.RunPython(create_default_categories, remove_default_categories),
    ]
