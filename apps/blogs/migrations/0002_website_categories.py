"""
Seed the blog topics the public website's blog slider labels posts with.

Unlike events, ``Blog.categories`` is optional, so this is convenience rather
than a hard requirement - but having the vocabulary in place means an editor
picks a topic from a list instead of inventing a new spelling each time.
"""

from django.db import migrations
from django.utils.text import slugify

BLOG_CATEGORIES = (
    ("Leadership", "Management thinking and leadership practice.", 10),
    ("Career", "Career paths, interviews and placement guidance.", 20),
    ("Industry", "Sector trends and what employers are looking for.", 30),
    ("Campus Life", "Student life on campus.", 40),
    ("Research", "Faculty and student research.", 50),
    ("Finance", "Finance, fintech and capital markets.", 60),
)


def create_blog_categories(apps, schema_editor):
    BlogCategory = apps.get_model("blogs", "BlogCategory")
    for name, description, order in BLOG_CATEGORIES:
        BlogCategory.objects.update_or_create(
            slug=slugify(name),
            defaults={"name": name, "description": description, "display_order": order, "is_active": True},
        )


def remove_blog_categories(apps, schema_editor):
    BlogCategory = apps.get_model("blogs", "BlogCategory")
    # Leave any category that posts still reference.
    for name, _, _ in BLOG_CATEGORIES:
        BlogCategory.objects.filter(slug=slugify(name), blogs__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [("blogs", "0001_initial")]

    operations = [
        migrations.RunPython(create_blog_categories, remove_blog_categories),
    ]
