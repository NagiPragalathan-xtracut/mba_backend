"""Tests for the common news / events / blogs feed."""

from datetime import date, time

from django.test import TestCase
from rest_framework.test import APITestCase

from apps.blogs.models import Blog, BlogCategory
from apps.core.models import Course, Department
from apps.core.utils import dotted_date, format_clock_time, html_paragraphs, long_date, short_date
from apps.events.models import Event, EventCategory

FEED_URL = "/api/v1/news-events/"
CATEGORIES_URL = "/api/v1/news-events/categories/"


class FormattingHelperTests(TestCase):
    """The date and text helpers the feed pre-formats every field with."""

    def test_short_date_is_day_and_abbreviated_month(self):
        self.assertEqual(short_date(date(2024, 12, 18)), "18 Dec")

    def test_short_date_pads_a_single_digit_day(self):
        self.assertEqual(short_date(date(2024, 12, 8)), "08 Dec")

    def test_long_date_includes_the_year(self):
        self.assertEqual(long_date(date(2025, 1, 15)), "15 Jan 2025")

    def test_dotted_date_is_day_month_year(self):
        self.assertEqual(dotted_date(date(2024, 12, 18)), "18.12.2024")

    def test_date_helpers_accept_an_iso_string(self):
        # Django leaves a freshly assigned DateField as the string it was given.
        self.assertEqual(short_date("2024-12-18"), "18 Dec")

    def test_date_helpers_return_empty_for_no_date(self):
        self.assertEqual(short_date(None), "")
        self.assertEqual(long_date(""), "")
        self.assertEqual(dotted_date(None), "")

    def test_clock_time_uses_a_twelve_hour_clock(self):
        self.assertEqual(format_clock_time(time(10, 0)), "10:00 AM")
        self.assertEqual(format_clock_time(time(17, 0)), "5:00 PM")

    def test_clock_time_renders_noon_and_midnight_as_twelve(self):
        self.assertEqual(format_clock_time(time(12, 30)), "12:30 PM")
        self.assertEqual(format_clock_time(time(0, 5)), "12:05 AM")

    def test_paragraphs_split_on_block_elements(self):
        self.assertEqual(html_paragraphs("<p>One.</p><p>Two.</p>"), ["One.", "Two."])

    def test_paragraphs_drop_empty_spacer_blocks(self):
        self.assertEqual(html_paragraphs("<p>One.</p><p>&nbsp;</p><p>Two.</p>"), ["One.", "Two."])

    def test_paragraphs_of_empty_content_is_an_empty_list(self):
        self.assertEqual(html_paragraphs(""), [])
        self.assertEqual(html_paragraphs(None), [])


class EventTimingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.get(slug="events")

    def make_event(self, **overrides):
        defaults = {"title": "Conclave", "category": self.category, "content": "<p>Body.</p>"}
        return Event.objects.create(**{**defaults, **overrides})

    def test_timing_is_a_range_when_both_times_are_set(self):
        event = self.make_event(start_time=time(10, 0), end_time=time(11, 0))
        self.assertEqual(event.timing_label, "10:00 AM – 11:00 AM")

    def test_timing_is_the_start_alone_when_there_is_no_end(self):
        self.assertEqual(self.make_event(start_time=time(9, 30)).timing_label, "9:30 AM")

    def test_timing_is_empty_without_a_start_time(self):
        # News and announcements have no clock time; the website hides the line.
        self.assertEqual(self.make_event(end_time=time(11, 0)).timing_label, "")


class FeedListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="School of Management", short_name="SOM")
        cls.event_category = EventCategory.objects.get(slug="events")
        cls.news_category = EventCategory.objects.get(slug="news")
        cls.blog_category = BlogCategory.objects.get(slug="leadership")

        cls.event = Event.objects.create(
            title="Drug Awareness Programme",
            category=cls.event_category,
            content="<p>First.</p><p>Second.</p>",
            event_date=date(2024, 12, 18),
            start_time=time(10, 0),
            end_time=time(11, 0),
            venue="Seminar Hall",
            display_order=10,
        )
        cls.event.departments.set([cls.department])

        cls.news = Event.objects.create(
            title="Ranked Among the Top 50",
            category=cls.news_category,
            content="<p>Recognition.</p>",
            event_date=date(2024, 12, 10),
            display_order=20,
        )

        cls.blog = Blog.objects.create(
            title="The Future of MBA Education",
            content="<p>Alpha.</p><p>Beta.</p>",
            published_date=date(2025, 1, 15),
            author_name="SRM B-School",
            display_order=10,
        )
        cls.blog.categories.set([cls.blog_category])

        cls.draft = Event.objects.create(
            title="Unpublished Draft",
            category=cls.event_category,
            content="<p>Not ready.</p>",
            is_published=False,
        )

    def get_feed(self, **params):
        return self.client.get(FEED_URL, params).json()

    # -- shape ---------------------------------------------------------

    def test_events_and_blogs_arrive_in_one_listing(self):
        types = {item["type"] for item in self.get_feed(page_size=100)["results"]}
        self.assertEqual(types, {"event", "blog"})

    def test_an_event_is_formatted_for_the_website(self):
        [item] = [i for i in self.get_feed(page_size=100)["results"] if i["slug"] == self.event.slug]

        self.assertEqual(item["type"], "event")
        self.assertEqual(item["title"], "Drug Awareness Programme")
        self.assertEqual(item["category"], "Events")
        self.assertEqual(item["date"], "18 Dec")
        self.assertEqual(item["date_label"], "18.12.2024")
        self.assertEqual(item["date_iso"], "2024-12-18")
        self.assertEqual(item["timing"], "10:00 AM – 11:00 AM")
        self.assertEqual(item["venue"], "Seminar Hall")
        self.assertEqual(item["paragraphs"], ["First.", "Second."])
        self.assertEqual(item["href"], f"/news-events/{self.event.slug}")
        self.assertEqual(item["departments"], ["School of Management"])

    def test_a_blog_is_formatted_for_the_website(self):
        [item] = [i for i in self.get_feed(page_size=100)["results"] if i["slug"] == self.blog.slug]

        self.assertEqual(item["type"], "blog")
        self.assertEqual(item["category"], "Leadership")
        self.assertEqual(item["date_long"], "15 Jan 2025")
        self.assertEqual(item["timing"], "")
        self.assertEqual(item["author"], "SRM B-School")
        self.assertEqual(item["paragraphs"], ["Alpha.", "Beta."])
        self.assertEqual(item["href"], f"/news-events/blog/{self.blog.slug}")
        self.assertGreaterEqual(item["reading_time_minutes"], 1)

    def test_every_item_carries_generated_seo_metadata(self):
        for item in self.get_feed(page_size=100)["results"]:
            self.assertTrue(item["seo"]["meta_title"], item["slug"])
            self.assertTrue(item["seo"]["meta_description"], item["slug"])

    # -- visibility ----------------------------------------------------

    def test_drafts_are_hidden_from_anonymous_callers(self):
        slugs = [item["slug"] for item in self.get_feed(page_size=100)["results"]]
        self.assertNotIn(self.draft.slug, slugs)

    # -- filtering -----------------------------------------------------

    def test_type_narrows_the_feed_to_one_source(self):
        results = self.get_feed(type="event", page_size=100)["results"]
        self.assertTrue(results)
        self.assertTrue(all(item["type"] == "event" for item in results))

    def test_an_unknown_type_is_rejected(self):
        self.assertEqual(self.client.get(FEED_URL, {"type": "podcast"}).status_code, 400)

    def test_category_filters_across_both_sources(self):
        results = self.get_feed(category="leadership", page_size=100)["results"]
        self.assertEqual([item["slug"] for item in results], [self.blog.slug])

    def test_category_all_is_treated_as_no_filter(self):
        self.assertEqual(self.get_feed(category="all", page_size=100)["count"], 3)

    def test_department_filters_across_both_sources(self):
        results = self.get_feed(department="school-of-management", page_size=100)["results"]
        self.assertEqual([item["slug"] for item in results], [self.event.slug])

    def test_search_matches_titles(self):
        results = self.get_feed(search="Awareness", page_size=100)["results"]
        self.assertEqual([item["slug"] for item in results], [self.event.slug])

    def test_date_bounds_apply_to_both_sources(self):
        results = self.get_feed(date_from="2025-01-01", page_size=100)["results"]
        self.assertEqual([item["slug"] for item in results], [self.blog.slug])

    # -- ordering ------------------------------------------------------

    def test_events_are_ordered_by_editor_rank_then_newest(self):
        results = self.get_feed(type="event", page_size=100)["results"]
        self.assertEqual([item["slug"] for item in results], [self.event.slug, self.news.slug])


class FeedDetailTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = Event.objects.create(
            title="Shared Slug",
            category=EventCategory.objects.get(slug="events"),
            content="<p>Event body.</p>",
            event_date=date(2024, 12, 18),
        )
        cls.blog = Blog.objects.create(title="A Post", content="<p>Post body.</p>")
        cls.draft = Blog.objects.create(title="Draft Post", content="<p>x</p>", is_published=False)

    def test_an_event_resolves_by_slug(self):
        response = self.client.get(f"{FEED_URL}{self.event.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["type"], "event")

    def test_an_item_resolves_by_numeric_id(self):
        response = self.client.get(f"{FEED_URL}{self.event.pk}/", {"type": "event"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], self.event.slug)

    def test_type_restricts_which_table_is_searched(self):
        # The slug is an event's; asking for a blog must not fall through to it.
        response = self.client.get(f"{FEED_URL}{self.event.slug}/", {"type": "blog"})
        self.assertEqual(response.status_code, 404)

    def test_an_unknown_identifier_is_a_404(self):
        self.assertEqual(self.client.get(f"{FEED_URL}no-such-thing/").status_code, 404)

    def test_a_draft_is_not_reachable_anonymously(self):
        self.assertEqual(self.client.get(f"{FEED_URL}{self.draft.slug}/").status_code, 404)


class FeedCategoryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.blog = Blog.objects.create(title="Campus Story", content="<p>Body.</p>")
        cls.blog.categories.set([BlogCategory.objects.get(slug="campus-life")])

        cls.event = Event.objects.create(
            title="Campus Fest",
            category=EventCategory.objects.get(slug="campus-life"),
            content="<p>Body.</p>",
        )

    def test_a_slug_shared_by_both_sources_is_listed_once(self):
        rows = self.client.get(CATEGORIES_URL).json()
        campus = [row for row in rows if row["slug"] == "campus-life"]

        self.assertEqual(len(campus), 1, "Campus Life must not appear twice in the sidebar")
        self.assertCountEqual(campus[0]["sources"], ["event", "blog"])
        # One published entry on each side.
        self.assertEqual(campus[0]["count"], 2)

    def test_type_returns_only_that_side(self):
        rows = self.client.get(CATEGORIES_URL, {"type": "blog"}).json()
        self.assertTrue(all(row["sources"] == ["blog"] for row in rows))

    def test_inactive_categories_are_omitted(self):
        EventCategory.objects.filter(slug="press-release").update(is_active=False)
        slugs = [row["slug"] for row in self.client.get(CATEGORIES_URL, {"type": "event"}).json()]
        self.assertNotIn("press-release", slugs)

    def test_an_unknown_type_is_rejected(self):
        self.assertEqual(self.client.get(CATEGORIES_URL, {"type": "podcast"}).status_code, 400)


class FeedCourseTests(APITestCase):
    """The Courses filter shared by events and blogs."""

    COURSES_URL = "/api/v1/news-events/courses/"

    @classmethod
    def setUpTestData(cls):
        cls.mba = Course.objects.get(slug="mba")
        cls.finance = Course.objects.get(slug="mba-finance")

        cls.event = Event.objects.create(
            title="Finance Summit",
            category=EventCategory.objects.get(slug="events"),
            content="<p>Body.</p>",
            event_date=date(2024, 12, 18),
        )
        cls.event.courses.set([cls.mba, cls.finance])

        cls.blog = Blog.objects.create(title="Fintech Careers", content="<p>Body.</p>")
        cls.blog.courses.set([cls.finance])

        cls.untagged = Event.objects.create(
            title="General Notice",
            category=EventCategory.objects.get(slug="news"),
            content="<p>Body.</p>",
        )

    def test_the_six_website_courses_are_seeded(self):
        slugs = [row["slug"] for row in self.client.get(self.COURSES_URL).json()]
        self.assertEqual(
            slugs,
            ["mba", "executive-mba", "mba-finance", "mba-marketing", "mba-hr", "mba-operations"],
        )

    def test_counts_span_both_sources(self):
        rows = {row["slug"]: row["count"] for row in self.client.get(self.COURSES_URL).json()}
        self.assertEqual(rows["mba-finance"], 2)  # one event + one post
        self.assertEqual(rows["mba"], 1)
        self.assertEqual(rows["mba-marketing"], 0)

    def test_inactive_courses_are_omitted(self):
        Course.objects.filter(slug="mba-hr").update(is_active=False)
        slugs = [row["slug"] for row in self.client.get(self.COURSES_URL).json()]
        self.assertNotIn("mba-hr", slugs)

    def test_the_feed_filters_by_course_across_both_sources(self):
        results = self.client.get(FEED_URL, {"course": "mba-finance", "page_size": 100}).json()["results"]
        self.assertCountEqual(
            [item["slug"] for item in results], [self.event.slug, self.blog.slug]
        )

    def test_an_untagged_entry_is_excluded_by_a_course_filter(self):
        results = self.client.get(FEED_URL, {"course": "mba", "page_size": 100}).json()["results"]
        self.assertNotIn(self.untagged.slug, [item["slug"] for item in results])

    def test_course_all_is_treated_as_no_filter(self):
        response = self.client.get(FEED_URL, {"course": "all", "page_size": 100}).json()
        self.assertEqual(response["count"], 3)

    def test_course_and_category_narrow_together(self):
        results = self.client.get(
            FEED_URL, {"course": "mba-finance", "category": "events", "page_size": 100}
        ).json()["results"]
        self.assertEqual([item["slug"] for item in results], [self.event.slug])

    def test_feed_items_carry_their_course_names_and_slugs(self):
        [item] = [
            i
            for i in self.client.get(FEED_URL, {"page_size": 100}).json()["results"]
            if i["slug"] == self.event.slug
        ]
        self.assertCountEqual(item["courses"], ["MBA", "MBA (Finance)"])
        self.assertCountEqual(item["course_slugs"], ["mba", "mba-finance"])

    def test_courses_are_writable_by_slug_through_the_events_api(self):
        self.event.courses.set([])
        response = self.client.patch(
            f"/api/v1/events/{self.event.slug}/", {"courses": ["mba-hr"]}, format="json"
        )
        # Writes need a token; an anonymous caller must be refused.
        self.assertEqual(response.status_code, 401)
