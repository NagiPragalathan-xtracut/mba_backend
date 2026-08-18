"""
Seed the programmes the website's Courses filter offers.

These are the six entries the News & Events sidebar lists. Kept as data rather
than a fixed choice list so the marketing team can add a programme without a
code change. Re-runnable and reversible.
"""

from django.db import migrations
from django.utils.text import slugify

DEFAULT_COURSES = (
    ("MBA", "MBA", "The flagship two-year Master of Business Administration.", 10),
    ("Executive MBA", "EMBA", "For working professionals.", 20),
    ("MBA (Finance)", "MBA-FIN", "Finance specialisation.", 30),
    ("MBA (Marketing)", "MBA-MKT", "Marketing specialisation.", 40),
    ("MBA (HR)", "MBA-HR", "Human resources specialisation.", 50),
    ("MBA (Operations)", "MBA-OPS", "Operations specialisation.", 60),
)


def create_default_courses(apps, schema_editor):
    Course = apps.get_model("core", "Course")
    for name, short_name, description, order in DEFAULT_COURSES:
        Course.objects.update_or_create(
            slug=slugify(name),
            defaults={
                "name": name,
                "short_name": short_name,
                "description": description,
                "display_order": order,
                "is_active": True,
            },
        )


def remove_default_courses(apps, schema_editor):
    Course = apps.get_model("core", "Course")
    # Leave any course that content still references.
    for name, _, _, _ in DEFAULT_COURSES:
        Course.objects.filter(slug=slugify(name), events__isnull=True, blogs__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_course"),
        # The reverse operation walks the reverse relations from Course, so the
        # migrations that create them have to be applied first.
        ("events", "0005_event_courses"),
        ("blogs", "0003_blog_courses"),
    ]

    operations = [
        migrations.RunPython(create_default_courses, remove_default_courses),
    ]
