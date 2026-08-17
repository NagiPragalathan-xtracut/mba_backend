"""
Tests for the SEO engine.

The behaviour that matters and is easy to break: blanks get filled, editor
input is never overwritten, and values derived from many-to-many relations are
refreshed once those relations exist.
"""

from django.test import TestCase, override_settings

from apps.core.models import Department
from apps.events.models import Event, EventCategory


@override_settings(SITE_NAME="Mohan Babu University", SITE_BASE_URL="https://example.edu")
class SEOGenerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Created by the events data migration, which the test database runs too.
        cls.category = EventCategory.objects.get(slug="upcoming")
        cls.cse = Department.objects.create(name="Computer Science & Engineering", short_name="CSE")
        cls.ece = Department.objects.create(name="Electronics & Communication", short_name="ECE")

    def make_event(self, **overrides):
        defaults = {
            "title": "National Tech Symposium",
            "category": self.category,
            "content": "<p>Two days of talks on applied AI and robotics.</p>",
        }
        return Event.objects.create(**{**defaults, **overrides})

    # --- generation ---------------------------------------------------

    def test_fills_blank_meta_title_with_site_suffix(self):
        event = self.make_event()
        self.assertEqual(event.meta_title, "National Tech Symposium | Mohan Babu University")

    def test_derives_meta_description_from_content_without_html(self):
        event = self.make_event()
        self.assertEqual(event.meta_description, "Two days of talks on applied AI and robotics.")
        self.assertNotIn("<", event.meta_description)

    def test_builds_canonical_url_from_slug(self):
        event = self.make_event()
        self.assertEqual(event.canonical_url, f"/events/{event.slug}/")

    def test_generates_schema_with_event_specifics(self):
        event = self.make_event(venue="Main Auditorium", event_date="2026-10-01")
        self.assertEqual(event.schema_json["@type"], "Event")
        self.assertEqual(event.schema_json["startDate"], "2026-10-01")
        self.assertEqual(event.schema_json["location"], {"@type": "Place", "name": "Main Auditorium"})
        self.assertEqual(event.schema_json["url"], f"https://example.edu/events/{event.slug}/")

    def test_twitter_falls_back_to_open_graph(self):
        event = self.make_event()
        self.assertEqual(event.twitter_title, event.og_title)
        self.assertEqual(event.twitter_card, "summary_large_image")

    # --- editor overrides ---------------------------------------------

    def test_editor_supplied_meta_title_is_kept(self):
        event = self.make_event(meta_title="Hand written title")
        self.assertEqual(event.meta_title, "Hand written title")

    def test_editor_supplied_title_survives_a_later_save(self):
        event = self.make_event(meta_title="Hand written title")
        event.title = "A completely different name"
        event.save()
        event.refresh_from_db()
        self.assertEqual(event.meta_title, "Hand written title")

    def test_editor_supplied_values_are_cleaned_of_html(self):
        event = self.make_event(meta_title="<b>Bold</b>   title")
        self.assertEqual(event.meta_title, "Bold title")

    def test_generated_title_refreshes_when_the_source_changes(self):
        event = self.make_event()
        event.title = "Renamed Symposium"
        event.save()
        event.refresh_from_db()
        self.assertEqual(event.meta_title, "Renamed Symposium | Mohan Babu University")

    # --- relation-dependent values ------------------------------------

    def test_keywords_ignore_relations_before_they_are_assigned(self):
        event = self.make_event()
        self.assertEqual(event.keywords, "national tech symposium")

    def test_sync_related_seo_adds_department_and_category_keywords(self):
        event = self.make_event()
        event.departments.set([self.cse, self.ece])
        event.sync_related_seo()
        event.refresh_from_db()

        self.assertIn("computer science & engineering", event.keywords)
        self.assertIn("electronics & communication", event.keywords)
        self.assertIn("upcoming", event.keywords)

    def test_sync_related_seo_leaves_editor_keywords_alone(self):
        event = self.make_event(keywords="one, two")
        event.departments.set([self.cse])
        event.sync_related_seo()
        event.refresh_from_db()
        self.assertEqual(event.keywords, "one, two")

    def test_update_fields_save_still_persists_generated_values(self):
        """`update_or_create` passes update_fields; derived values must survive."""
        event = self.make_event()
        Event.objects.update_or_create(slug=event.slug, defaults={"title": "Brand New Title"})
        event.refresh_from_db()
        self.assertEqual(event.meta_title, "Brand New Title | Mohan Babu University")
