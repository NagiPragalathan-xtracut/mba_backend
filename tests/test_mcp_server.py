"""
Tests for the MCP server.

The HTTP layer is stubbed - what matters here is the glue: every tool is
registered, arguments are shaped correctly before they reach the API, and
failures come back as messages a model can act on.
"""

import asyncio
import json
from unittest.mock import patch

from django.test import SimpleTestCase

from mcp_server.client import APIError, MBUClient
from mcp_server.config import Settings
from mcp_server.server import build_server
from mcp_server.tools._common import as_paragraphs, compact, listing, split_csv

SETTINGS = Settings(api_base_url="http://testserver", api_token="test-token", timeout=5)


class RecordingClient(MBUClient):
    """Client that records calls instead of making them."""

    def __init__(self):
        super().__init__(SETTINGS)
        self.calls = []
        self.response = {}

    def _request(self, method, path, **kwargs):
        self.calls.append({"method": method, "path": path, **kwargs})
        return self.response


def run(coro):
    return asyncio.run(coro)


class CommonHelperTests(SimpleTestCase):
    def test_split_csv_trims_and_drops_blanks(self):
        self.assertEqual(split_csv("cse, ece ,, mech"), ["cse", "ece", "mech"])

    def test_split_csv_passes_none_through(self):
        """`None` means "not supplied" and must not become an empty list."""
        self.assertIsNone(split_csv(None))

    def test_as_paragraphs_wraps_plain_text(self):
        self.assertEqual(as_paragraphs("One.\n\nTwo."), "<p>One.</p><p>Two.</p>")

    def test_as_paragraphs_leaves_existing_html_alone(self):
        html = "<ul><li>Item</li></ul>"
        self.assertEqual(as_paragraphs(html), html)

    def test_compact_keeps_only_present_keys(self):
        self.assertEqual(compact({"a": 1, "b": 2}, ("a", "zz")), {"a": 1})

    def test_listing_summarises_a_paginated_response(self):
        result = listing(
            {"count": 2, "total_pages": 1, "current_page": 1, "next": None,
             "results": [{"id": 1, "name": "A", "extra": "drop"}]},
            ("id", "name"),
        )
        self.assertEqual(result["count"], 2)
        self.assertFalse(result["has_more"])
        self.assertEqual(result["results"], [{"id": 1, "name": "A"}])


class ClientErrorTests(SimpleTestCase):
    def test_missing_image_file_is_reported_clearly(self):
        client = MBUClient(SETTINGS)
        with self.assertRaises(APIError) as ctx:
            client.upload("events/x/images/", "/definitely/not/here.png")
        self.assertIn("Pass an absolute path", str(ctx.exception))

    def test_unsupported_file_type_is_rejected_before_upload(self):
        client = MBUClient(SETTINGS)
        with patch("pathlib.Path.is_file", return_value=True):
            with self.assertRaises(APIError) as ctx:
                client.upload("events/x/images/", "/tmp/notes.txt")
        self.assertIn("not a supported image type", str(ctx.exception))

    def test_none_values_are_stripped_from_payloads(self):
        self.assertEqual(MBUClient._clean({"a": 1, "b": None}), {"a": 1})


class ToolRegistrationTests(SimpleTestCase):
    def test_every_expected_tool_is_registered(self):
        tools = {tool.name for tool in run(build_server().list_tools())}
        expected = {
            "check_backend",
            "list_departments", "create_department",
            "list_event_categories", "create_event_category",
            "list_blog_categories", "create_blog_category",
            "list_designations", "create_designation",
            "list_events", "get_event", "create_event", "update_event",
            "upload_event_image", "set_event_featured_image", "delete_event",
            "list_blogs", "get_blog", "create_blog", "update_blog",
            "set_blog_cover_image", "upload_blog_image", "delete_blog",
            "list_faculty", "get_faculty", "create_faculty", "update_faculty",
            "add_faculty_section", "update_faculty_section", "delete_faculty_section",
            "set_faculty_photo", "upload_faculty_banner", "delete_faculty",
        }
        self.assertEqual(expected - tools, set(), "tools are missing from the server")

    def test_every_tool_has_a_description(self):
        for tool in run(build_server().list_tools()):
            with self.subTest(tool=tool.name):
                self.assertTrue(tool.description, f"{tool.name} has no docstring")


class ToolBehaviourTests(SimpleTestCase):
    """Calls each tool against a recording client to check the request it builds."""

    def setUp(self):
        from mcp.server.fastmcp import FastMCP

        from mcp_server.tools import register_all

        self.client = RecordingClient()
        self.mcp = FastMCP(name="test")
        register_all(self.mcp, self.client)

    def call(self, tool, **kwargs):
        result = run(self.mcp.call_tool(tool, kwargs))
        content, structured = result if isinstance(result, tuple) else (result, None)
        if isinstance(structured, dict):
            return structured
        for block in content:
            if getattr(block, "text", None):
                return json.loads(block.text)
        return {}

    def test_create_event_sends_slug_lists_and_html(self):
        self.client.response = {"id": 1, "slug": "x", "title": "Symposium"}
        self.call(
            "create_event",
            title="Symposium", category="upcoming",
            departments="cse, ece", content="Line one.\n\nLine two.",
        )

        payload = self.client.calls[0]["json"]
        self.assertEqual(self.client.calls[0]["method"], "POST")
        self.assertEqual(payload["departments"], ["cse", "ece"])
        self.assertEqual(payload["content"], "<p>Line one.</p><p>Line two.</p>")

    def test_update_event_omits_arguments_that_were_not_passed(self):
        self.client.response = {"id": 1, "slug": "x"}
        self.call("update_event", identifier="x", venue="Hall A")

        payload = self.client.calls[0]["json"]
        self.assertEqual(self.client.calls[0]["method"], "PATCH")
        self.assertEqual(set(payload), {"venue", "is_published", "is_featured"} & set(payload))
        self.assertNotIn("title", payload)
        self.assertNotIn("departments", payload)

    def test_add_faculty_section_targets_the_nested_route(self):
        self.client.response = {"id": 5, "heading": "Awards"}
        self.call("add_faculty_section", identifier="dr-rao", heading="Awards", content="Won things.")

        call = self.client.calls[0]
        self.assertEqual(call["path"], "faculty/dr-rao/sections/")
        self.assertEqual(call["json"]["content"], "<p>Won things.</p>")

    def test_list_events_drops_unset_filters(self):
        self.client.response = {"count": 0, "results": []}
        self.call("list_events", category="upcoming")
        self.assertEqual(self.client.calls[0]["params"], {"category": "upcoming"})

    def test_delete_event_reports_what_it_removed(self):
        self.client.response = {}
        result = self.call("delete_event", identifier="old-event")
        self.assertEqual(result["status"], "deleted")
        self.assertEqual(self.client.calls[0]["method"], "DELETE")
