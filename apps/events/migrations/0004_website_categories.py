"""
Add the categories the public website's News & Events sidebar offers.

The page filters by News, Events, Announcements, Press Release and Campus Life.
"Upcoming" and "Achievements" from migration 0002 stay - they are the editorial
categories used inside the admin - so both vocabularies coexist and the
frontend simply lists whatever the categories endpoint returns.

Re-runnable and reversible, like 0002.
"""

from django.db import migrations
from django.utils.text import slugify

WEBSITE_CATEGORIES = (
    ("News", "Institutional news and press coverage.", 30),
    ("Events", "Seminars, conclaves, workshops and campus programmes.", 40),
    ("Announcements", "Official notices, admissions and deadlines.", 50),
    ("Press Release", "Statements issued to the press.", 60),
    ("Campus Life", "Student life, clubs, sports and culture.", 70),
)


def create_website_categories(apps, schema_editor):
    EventCategory = apps.get_model("events", "EventCategory")
    for name, description, order in WEBSITE_CATEGORIES:
        EventCategory.objects.update_or_create(
            slug=slugify(name),
            defaults={"name": name, "description": description, "display_order": order, "is_active": True},
        )


def remove_website_categories(apps, schema_editor):
    EventCategory = apps.get_model("events", "EventCategory")
    # Categories still referenced by an event are left alone; the PROTECT
    # constraint on Event.category would reject the delete anyway.
    for name, _, _ in WEBSITE_CATEGORIES:
        EventCategory.objects.filter(slug=slugify(name), events__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [("events", "0003_event_end_time_event_start_time")]

    operations = [
        migrations.RunPython(create_website_categories, remove_website_categories),
    ]
