"""Tests for the shared text and slug helpers."""

from django.test import TestCase

from apps.core.models import Department
from apps.core.utils.slugs import unique_slugify
from apps.core.utils.text import clean_whitespace, strip_html, summarise


class StripHtmlTests(TestCase):
    def test_removes_tags_and_unescapes_entities(self):
        self.assertEqual(strip_html("<p>Hello <b>world</b> &amp; friends</p>"), "Hello world & friends")

    def test_removes_script_and_style_bodies_entirely(self):
        html = "<p>Safe</p><script>alert('x')</script><style>.a{color:red}</style>"
        self.assertEqual(strip_html(html), "Safe")

    def test_handles_none_and_empty(self):
        self.assertEqual(strip_html(None), "")
        self.assertEqual(strip_html(""), "")


class CleanWhitespaceTests(TestCase):
    def test_collapses_runs_and_trims(self):
        self.assertEqual(clean_whitespace("  a \n\n  b\tc  "), "a b c")


class SummariseTests(TestCase):
    def test_returns_short_text_unchanged(self):
        self.assertEqual(summarise("<p>Short</p>", 100), "Short")

    def test_truncates_on_a_word_boundary(self):
        result = summarise("alpha beta gamma delta epsilon", 20)
        self.assertLessEqual(len(result), 20)
        self.assertTrue(result.endswith("…"))
        # Must not cut a word in half.
        self.assertNotIn("gam…", result)

    def test_strips_html_before_measuring(self):
        self.assertEqual(summarise("<p><b>Hi</b> there</p>", 50), "Hi there")


class UniqueSlugifyTests(TestCase):
    def test_generates_slug_from_value(self):
        department = Department(name="Computer Science")
        self.assertEqual(unique_slugify(department, "Computer Science"), "computer-science")

    def test_appends_suffix_when_taken(self):
        Department.objects.create(name="Physics", slug="physics")
        self.assertEqual(unique_slugify(Department(name="Physics II"), "Physics"), "physics-1")

    def test_excludes_self_so_resaving_keeps_the_slug(self):
        department = Department.objects.create(name="Chemistry", slug="chemistry")
        self.assertEqual(unique_slugify(department, "Chemistry"), "chemistry")

    def test_falls_back_when_value_has_no_slug_characters(self):
        self.assertEqual(unique_slugify(Department(name="!!!"), "!!!"), "item")
