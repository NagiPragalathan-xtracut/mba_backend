"""Tests for blog posts."""

from django.test import TestCase
from django.utils import timezone

from apps.blogs.models import Blog, BlogCategory
from apps.core.models import Department


class BlogModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Seeded by the blogs/0002_website_categories data migration.
        cls.research = BlogCategory.objects.get(slug="research")
        cls.campus = BlogCategory.objects.get(slug="campus-life")
        cls.department = Department.objects.create(name="Computer Science", short_name="CSE")

    def make_blog(self, title="Life in the Robotics Lab", **overrides):
        defaults = {"content": "<p>Building robots since 2019.</p>"}
        return Blog.objects.create(title=title, **{**defaults, **overrides})

    def test_slug_is_generated_from_the_title(self):
        self.assertEqual(self.make_blog().slug, "life-in-the-robotics-lab")

    def test_published_date_defaults_to_today(self):
        self.assertEqual(self.make_blog().published_date, timezone.localdate())

    def test_cover_alt_text_defaults_to_the_title(self):
        self.assertEqual(self.make_blog().featured_image_alt, "Life in the Robotics Lab")

    def test_summary_is_derived_as_plain_text(self):
        self.assertEqual(self.make_blog().summary, "Building robots since 2019.")

    def test_reading_time_is_at_least_one_minute(self):
        self.assertEqual(self.make_blog(content="<p>Tiny.</p>").reading_time_minutes, 1)

    def test_reading_time_scales_with_length(self):
        blog = self.make_blog(content="<p>" + ("word " * 600) + "</p>")
        self.assertEqual(blog.reading_time_minutes, 3)

    def test_a_post_can_have_several_categories(self):
        blog = self.make_blog()
        blog.categories.set([self.research, self.campus])
        self.assertEqual(blog.categories.count(), 2)

    def test_schema_is_a_blog_posting_with_dates(self):
        blog = self.make_blog(author_name="Lab Team")
        self.assertEqual(blog.schema_json["@type"], "BlogPosting")
        self.assertEqual(blog.schema_json["datePublished"], blog.published_date.isoformat())
        self.assertEqual(blog.schema_json["author"], {"@type": "Person", "name": "Lab Team"})

    def test_keywords_pick_up_categories_after_sync(self):
        blog = self.make_blog()
        blog.categories.set([self.research])
        blog.departments.set([self.department])
        blog.sync_related_seo()
        blog.refresh_from_db()

        self.assertIn("research", blog.keywords)
        self.assertIn("computer science", blog.keywords)

    def test_ordering_puts_display_order_first(self):
        self.make_blog(title="Second", display_order=20)
        self.make_blog(title="First", display_order=10)
        self.assertEqual([blog.title for blog in Blog.objects.all()], ["First", "Second"])
