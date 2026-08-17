"""Tests for event models, especially the featured-image rules."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.core.models import Department
from apps.events.models import Event, EventCategory, EventImage

# A 1x1 GIF - the smallest thing Django will accept as an image.
TINY_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)


def image_file(name="photo.gif"):
    return SimpleUploadedFile(name, TINY_GIF, content_type="image/gif")


class EventModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Created by the events data migration, which the test database runs too.
        cls.category = EventCategory.objects.get(slug="upcoming")
        cls.department = Department.objects.create(name="Computer Science", short_name="CSE")

    def make_event(self, title="Orientation Day", **overrides):
        return Event.objects.create(
            title=title, category=self.category,
            content=overrides.pop("content", "<p>Welcome to campus.</p>"), **overrides,
        )

    def test_slug_is_generated_from_the_title(self):
        self.assertEqual(self.make_event().slug, "orientation-day")

    def test_duplicate_titles_get_distinct_slugs(self):
        first, second = self.make_event(), self.make_event()
        self.assertEqual(first.slug, "orientation-day")
        self.assertEqual(second.slug, "orientation-day-1")

    def test_summary_is_derived_from_content_as_plain_text(self):
        event = self.make_event(content="<p>A <b>great</b> day.</p>")
        self.assertEqual(event.summary, "A great day.")

    def test_explicit_summary_is_kept(self):
        self.assertEqual(self.make_event(summary="Mine").summary, "Mine")

    def test_featured_image_is_none_before_the_event_is_saved(self):
        self.assertIsNone(Event(title="Draft", category=self.category).featured_image)


class EventImageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Created by the events data migration, which the test database runs too.
        cls.category = EventCategory.objects.get(slug="upcoming")

    def setUp(self):
        self.event = Event.objects.create(title="Sports Day", category=self.category, content="<p>Run.</p>")

    def test_first_image_becomes_featured_automatically(self):
        image = EventImage.objects.create(event=self.event, image=image_file())
        self.assertTrue(image.is_featured)
        self.assertEqual(self.event.featured_image, image)

    def test_second_image_is_not_featured_by_default(self):
        EventImage.objects.create(event=self.event, image=image_file("a.gif"))
        second = EventImage.objects.create(event=self.event, image=image_file("b.gif"))
        self.assertFalse(second.is_featured)

    def test_featuring_an_image_demotes_the_previous_one(self):
        first = EventImage.objects.create(event=self.event, image=image_file("a.gif"))
        second = EventImage.objects.create(event=self.event, image=image_file("b.gif"))

        second.is_featured = True
        second.save()

        first.refresh_from_db()
        self.assertFalse(first.is_featured)
        self.assertEqual(self.event.featured_image, second)

    def test_database_rejects_two_featured_images_for_one_event(self):
        EventImage.objects.create(event=self.event, image=image_file("a.gif"))
        # Bypass the model's save() to prove the constraint itself holds.
        with self.assertRaises(IntegrityError), transaction.atomic():
            EventImage.objects.bulk_create(
                [EventImage(event=self.event, image="events/gallery/b.gif", is_featured=True)]
            )

    def test_alt_text_falls_back_to_the_event_title(self):
        image = EventImage.objects.create(event=self.event, image=image_file())
        self.assertEqual(image.alt, "Sports Day")

    def test_alt_text_prefers_the_caption(self):
        image = EventImage.objects.create(event=self.event, image=image_file(), caption="Relay race")
        self.assertEqual(image.alt, "Relay race")

    def test_events_do_not_share_featured_images(self):
        other = Event.objects.create(title="Quiz Day", category=self.category, content="<p>Quiz.</p>")
        first = EventImage.objects.create(event=self.event, image=image_file("a.gif"))
        second = EventImage.objects.create(event=other, image=image_file("b.gif"))

        # Each event independently features its own first photo.
        self.assertTrue(first.is_featured)
        self.assertTrue(second.is_featured)
