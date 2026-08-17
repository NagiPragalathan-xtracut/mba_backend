"""
API tests.

Covers the contract external clients (the website and the MCP server) depend
on: reads are public, writes need a token, relations are addressed by slug, and
detail routes accept slug / id / UUID interchangeably.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.blogs.models import Blog, BlogCategory
from apps.core.models import Department
from apps.events.models import Event, EventCategory, EventImage
from apps.faculty.models import Designation, Faculty, FacultySection

TINY_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)


class APITestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="editor", password="x")
        cls.token = Token.objects.create(user=cls.user)

        cls.department = Department.objects.create(name="Computer Science", short_name="CSE")
        # "Upcoming" is created by the events data migration, which the test
        # database also runs - reuse it instead of clashing with it.
        cls.event_category = EventCategory.objects.get(slug="upcoming")
        cls.blog_category = BlogCategory.objects.create(name="Research")
        cls.designation = Designation.objects.create(name="Professor")

    def authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")


class PermissionTests(APITestBase):
    def test_anonymous_users_can_read(self):
        self.assertEqual(self.client.get("/api/v1/events/").status_code, 200)

    def test_anonymous_users_cannot_write(self):
        response = self.client.post("/api/v1/events/", {"title": "X", "category": "upcoming", "content": "x"})
        self.assertEqual(response.status_code, 401)

    def test_a_token_allows_writing(self):
        self.authenticate()
        response = self.client.post(
            "/api/v1/events/",
            {"title": "Convocation", "category": "upcoming", "content": "<p>Ceremony.</p>"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_drafts_are_hidden_from_anonymous_callers(self):
        Event.objects.create(title="Secret", category=self.event_category, content="x", is_published=False)
        self.assertEqual(self.client.get("/api/v1/events/").data["count"], 0)

        self.authenticate()
        self.assertEqual(self.client.get("/api/v1/events/").data["count"], 1)


class EventAPITests(APITestBase):
    def setUp(self):
        self.authenticate()

    def create_event(self, **overrides):
        payload = {
            "title": "National Symposium",
            "category": "upcoming",
            "content": "<p>Talks and workshops.</p>",
            "departments": ["computer-science"],
            **overrides,
        }
        return self.client.post("/api/v1/events/", payload, format="json")

    def test_relations_are_written_by_slug(self):
        response = self.create_event()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["category"], "upcoming")
        self.assertEqual(response.data["departments"], ["computer-science"])

    def test_unknown_slug_returns_a_helpful_message(self):
        response = self.create_event(category="nope")
        self.assertEqual(response.status_code, 400)
        self.assertIn("No Event Category exists with slug 'nope'", str(response.data["category"]))

    def test_seo_is_generated_and_includes_relations(self):
        slug = self.create_event().data["slug"]
        detail = self.client.get(f"/api/v1/events/{slug}/").data

        self.assertTrue(detail["seo"]["meta_title"])
        self.assertTrue(detail["seo"]["schema_json"])
        self.assertIn("computer science", detail["keywords"])

    def test_end_date_before_start_date_is_rejected(self):
        response = self.create_event(event_date="2026-05-05", end_date="2026-05-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_date", response.data)

    def test_detail_route_accepts_slug_id_and_uuid(self):
        slug = self.create_event().data["slug"]
        event = Event.objects.get(slug=slug)

        for identifier in (event.slug, str(event.pk), str(event.unique_id)):
            with self.subTest(identifier=identifier):
                self.assertEqual(self.client.get(f"/api/v1/events/{identifier}/").status_code, 200)

    def test_uploading_a_photo_features_it_when_asked(self):
        slug = self.create_event().data["slug"]

        first = self.client.post(
            f"/api/v1/events/{slug}/images/",
            {"image": SimpleUploadedFile("a.gif", TINY_GIF, content_type="image/gif"), "alt": "First"},
            format="multipart",
        )
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.data["is_featured"])  # first photo is featured automatically

        second = self.client.post(
            f"/api/v1/events/{slug}/images/",
            {
                "image": SimpleUploadedFile("b.gif", TINY_GIF, content_type="image/gif"),
                "alt": "Second",
                "is_featured": True,
            },
            format="multipart",
        )
        self.assertEqual(second.status_code, 201)

        self.assertEqual(EventImage.objects.filter(is_featured=True).count(), 1)
        self.assertEqual(EventImage.objects.get(is_featured=True).alt, "Second")

    def test_filters_work(self):
        self.create_event()
        self.create_event(title="Other", departments=[])

        self.assertEqual(self.client.get("/api/v1/events/?department=computer-science").data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/events/?category=upcoming").data["count"], 2)
        self.assertEqual(self.client.get("/api/v1/events/?search=Other").data["count"], 1)

    def test_list_response_is_paginated_with_helpful_metadata(self):
        self.create_event()
        data = self.client.get("/api/v1/events/").data
        for key in ("count", "total_pages", "current_page", "page_size", "results"):
            self.assertIn(key, data)


class FacultyAPITests(APITestBase):
    def setUp(self):
        self.authenticate()
        self.faculty = Faculty.objects.create(name="Dr. Anitha Rao", designation=self.designation)

    def test_sections_can_be_appended_through_the_detail_route(self):
        response = self.client.post(
            f"/api/v1/faculty/{self.faculty.slug}/sections/",
            {"heading": "Publications", "content": "<p>Papers.</p>"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(FacultySection.objects.count(), 1)

    def test_duplicate_headings_are_rejected(self):
        FacultySection.objects.create(faculty=self.faculty, heading="Awards", content="<p>a</p>")
        response = self.client.post(
            f"/api/v1/faculty/{self.faculty.slug}/sections/",
            {"heading": "Awards", "content": "<p>b</p>"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_detail_payload_nests_sections_in_order(self):
        for heading, order in (("Awards", 30), ("Biography", 10)):
            FacultySection.objects.create(
                faculty=self.faculty, heading=heading, content="<p>x</p>", display_order=order
            )

        data = self.client.get(f"/api/v1/faculty/{self.faculty.slug}/").data
        self.assertEqual([section["heading"] for section in data["sections"]], ["Biography", "Awards"])

    def test_has_email_filter(self):
        Faculty.objects.create(name="Dr. With Mail", designation=self.designation, mail_id="a@example.edu")
        self.assertEqual(self.client.get("/api/v1/faculty/?has_email=true").data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/faculty/?has_email=false").data["count"], 1)


class BlogAPITests(APITestBase):
    def setUp(self):
        self.authenticate()

    def test_a_post_can_be_created_with_several_categories(self):
        BlogCategory.objects.create(name="Campus Life")
        response = self.client.post(
            "/api/v1/blogs/",
            {
                "title": "Two Topics",
                "content": "<p>Body.</p>",
                "categories": ["research", "campus-life"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(sorted(response.data["categories"]), ["campus-life", "research"])

    def test_cover_image_can_be_patched_as_multipart(self):
        blog = Blog.objects.create(title="Cover Test", content="<p>x</p>")
        response = self.client.patch(
            f"/api/v1/blogs/{blog.slug}/",
            {"featured_image": SimpleUploadedFile("c.gif", TINY_GIF, content_type="image/gif")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["featured_image_url"])

    def test_reading_time_is_exposed(self):
        Blog.objects.create(title="Timed", content="<p>" + ("word " * 400) + "</p>")
        self.assertEqual(self.client.get("/api/v1/blogs/").data["results"][0]["reading_time_minutes"], 2)


class HealthTests(APITestBase):
    def test_health_reports_database_connectivity(self):
        data = self.client.get("/api/v1/health/").data
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertFalse(data["authenticated"])

    def test_health_reports_the_authenticated_user(self):
        self.authenticate()
        data = self.client.get("/api/v1/health/").data
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["user"], "editor")
