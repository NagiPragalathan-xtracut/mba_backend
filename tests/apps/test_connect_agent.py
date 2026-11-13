"""
Tests for issuing agent tokens and the admin's "Connect an AI agent" page.

What matters: only admins who may create users and tokens can use the page,
agent accounts can never log in, a person's login is never touched, the key is
shown once (and never in a URL), and the setup prompt carries everything an
agent needs to install the MCP server by itself.
"""

import json
import re
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token

from apps.core.agent_setup import MCP_REQUIREMENTS, SERVER_NAME, AgentSetup
from apps.core.tokens import TokenIssueError, agent_username, issue_token

User = get_user_model()
CONNECT_URL = "/admin/authtoken/tokenproxy/connect/"


class AgentUsernameTests(TestCase):
    def test_names_become_prefixed_slugs(self):
        self.assertEqual(agent_username("Claude Desktop (office)"), "mcp-claude-desktop-office")

    def test_existing_prefix_is_kept(self):
        self.assertEqual(agent_username("mcp-bot"), "mcp-bot")

    def test_names_without_letters_or_digits_are_rejected(self):
        self.assertEqual(agent_username("!!!"), "")


class IssueTokenTests(TestCase):
    def test_creates_a_token_only_account(self):
        issued = issue_token("mcp-new", create_user=True)

        user = User.objects.get(username="mcp-new")
        self.assertTrue(issued.user_created)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(issued.token.user, user)

    def test_returns_the_existing_token_unless_rotating(self):
        first = issue_token("mcp-new", create_user=True).token.key
        self.assertEqual(issue_token("mcp-new").token.key, first)

        rotated = issue_token("mcp-new", rotate=True)
        self.assertTrue(rotated.rotated)
        self.assertNotEqual(rotated.token.key, first)
        self.assertFalse(Token.objects.filter(key=first).exists())

    def test_missing_user_without_create_is_an_error(self):
        with self.assertRaises(TokenIssueError):
            issue_token("nobody")

    def test_agents_only_refuses_a_persons_login(self):
        User.objects.create_user(username="mcp-person", password="a-real-password")
        with self.assertRaises(TokenIssueError):
            issue_token("mcp-person", rotate=True, agents_only=True)
        self.assertFalse(Token.objects.filter(user__username="mcp-person").exists())


class CreateApiTokenCommandTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("create_api_token", *args, stdout=out)
        return out.getvalue()

    def test_creates_user_and_prints_the_key(self):
        output = self.run_command("--username", "mcp-bot", "--create-user")
        key = Token.objects.get(user__username="mcp-bot").key
        self.assertIn("Created user 'mcp-bot'", output)
        self.assertIn(f"MBU_API_TOKEN={key}", output)

    def test_second_run_reports_the_existing_token(self):
        self.run_command("--username", "mcp-bot", "--create-user")
        self.assertIn("This is the existing token", self.run_command("--username", "mcp-bot"))

    def test_rotate_replaces_the_key(self):
        self.run_command("--username", "mcp-bot", "--create-user")
        old = Token.objects.get(user__username="mcp-bot").key
        output = self.run_command("--username", "mcp-bot", "--rotate")
        self.assertIn("Previous token revoked", output)
        self.assertNotEqual(Token.objects.get(user__username="mcp-bot").key, old)

    def test_unknown_user_is_a_command_error(self):
        with self.assertRaises(CommandError):
            self.run_command("--username", "nobody")


class AgentSetupTests(TestCase):
    setup = AgentSetup(
        site_name="Test School",
        api_base_url="https://api.example.edu",
        token="abc123token",
        username="mcp-claude",
        repo_url="https://github.com/example/backend.git",
    )

    def test_prompt_carries_everything_the_agent_needs(self):
        prompt = self.setup.prompt()
        for expected in (
            "https://api.example.edu",
            "abc123token",
            "https://api.example.edu/api/v1/health/",
            '"user": "mcp-claude"',
            "git clone --depth 1 --branch main https://github.com/example/backend.git",
            "https://github.com/example/backend/archive/refs/heads/main.zip",
            f"claude mcp add --scope user",
            f"{SERVER_NAME} -- PYTHON -m mcp_server",
            *MCP_REQUIREMENTS,
        ):
            self.assertIn(expected, prompt)

    def test_client_config_is_valid_json(self):
        entry = json.loads(self.setup.client_config())["mcpServers"][SERVER_NAME]
        self.assertEqual(entry["args"], ["-m", "mcp_server"])
        self.assertEqual(entry["env"]["MBU_API_TOKEN"], "abc123token")
        self.assertEqual(entry["env"]["MBU_API_BASE_URL"], "https://api.example.edu")

    def test_pins_match_requirements_txt(self):
        """The prompt installs exactly what the MCP server is tested with."""
        requirements = (Path(settings.BASE_DIR) / "requirements.txt").read_text(encoding="utf-8")
        pinned = dict(re.findall(r"^([A-Za-z0-9_.-]+)==([^\s;]+)", requirements, re.MULTILINE))
        for requirement in MCP_REQUIREMENTS:
            name, version = requirement.split("==")
            self.assertEqual(pinned.get(name), version, f"{name} differs from requirements.txt")


class ConnectAgentPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(username="boss", email="", password="pw")
        cls.admin_token = Token.objects.create(user=cls.admin)
        cls.editor = User.objects.create_user(username="editor", password="pw", is_staff=True)

    def setUp(self):
        self.client.force_login(self.admin)

    def create(self, name, replace=False):
        data = {"action": "create", "name": name}
        if replace:
            data["replace"] = "on"
        return self.client.post(CONNECT_URL, data)

    # -- access -------------------------------------------------------------

    def test_url_name_resolves(self):
        self.assertEqual(reverse("admin:authtoken_tokenproxy_connect"), CONNECT_URL)

    def test_anonymous_users_are_sent_to_login(self):
        self.client.logout()
        response = self.client.get(CONNECT_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_staff_without_permission_are_refused(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(CONNECT_URL).status_code, 403)
        self.assertEqual(self.client.post(CONNECT_URL, {"action": "create", "name": "x"}).status_code, 403)
        self.assertFalse(User.objects.filter(username="mcp-x").exists())

    def test_admin_sees_the_page(self):
        response = self.client.get(CONNECT_URL)
        self.assertContains(response, "Connect an AI agent")
        self.assertContains(response, "Create token and setup prompt")
        self.assertNotContains(response, 'id="ca-prompt"')

    # -- creating -----------------------------------------------------------

    def test_creating_shows_the_prompt_once(self):
        response = self.create("Claude Desktop")
        self.assertRedirects(response, CONNECT_URL, fetch_redirect_response=False)

        user = User.objects.get(username="mcp-claude-desktop")
        self.assertFalse(user.has_usable_password())
        key = Token.objects.get(user=user).key
        self.assertNotIn(key, response["Location"])

        page = self.client.get(CONNECT_URL)
        self.assertContains(page, 'id="ca-prompt"')
        self.assertContains(page, key)
        self.assertContains(page, "http://testserver/api/v1/health/")
        self.assertContains(page, settings.AGENT_SETUP_REPO_URL)

        # Shown once: a reload no longer contains the key.
        self.assertNotContains(self.client.get(CONNECT_URL), key)

    def test_existing_agent_needs_replace(self):
        self.create("claude")
        key = Token.objects.get(user__username="mcp-claude").key

        response = self.create("claude")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has a token")
        self.assertEqual(Token.objects.get(user__username="mcp-claude").key, key)

        self.create("claude", replace=True)
        self.assertNotEqual(Token.objects.get(user__username="mcp-claude").key, key)
        self.assertFalse(Token.objects.filter(key=key).exists())

    def test_a_persons_login_is_never_touched(self):
        person = User.objects.create_user(username="mcp-person", password="a-real-password")
        Token.objects.create(user=person)
        key = person.auth_token.key

        response = self.create("mcp-person", replace=True)
        self.assertContains(response, "a person&#x27;s login")
        self.assertEqual(Token.objects.get(user=person).key, key)

    def test_name_without_usable_characters_is_rejected(self):
        self.assertContains(self.create("!!!"), "at least one letter or number")

    # -- the agents list ----------------------------------------------------

    def test_list_shows_agents_only(self):
        self.create("claude")
        page = self.client.get(CONNECT_URL)
        self.assertContains(page, "mcp-claude")
        self.assertNotContains(page, ">boss<")

    def test_setup_prompt_for_an_existing_agent(self):
        issue_token("mcp-bot", create_user=True)
        key = Token.objects.get(user__username="mcp-bot").key

        response = self.client.post(CONNECT_URL, {"action": "show", "username": "mcp-bot"})
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(CONNECT_URL), key)

    def test_setup_prompt_is_never_shown_for_a_persons_token(self):
        self.client.post(CONNECT_URL, {"action": "show", "username": "boss"})
        self.assertNotContains(self.client.get(CONNECT_URL), self.admin_token.key)

    def test_revoke_deletes_the_agents_token(self):
        self.create("claude")
        response = self.client.post(CONNECT_URL, {"action": "revoke", "username": "mcp-claude"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Token.objects.filter(user__username="mcp-claude").exists())

    def test_revoke_never_touches_a_persons_token(self):
        self.client.post(CONNECT_URL, {"action": "revoke", "username": "boss"})
        self.assertTrue(Token.objects.filter(key=self.admin_token.key).exists())

    def test_full_keys_never_appear_in_links(self):
        self.create("claude")
        key = Token.objects.get(user__username="mcp-claude").key
        self.client.get(CONNECT_URL)  # consumes the one-time result
        self.assertNotContains(self.client.get(CONNECT_URL), key)

    @override_settings(AGENT_SETUP_API_BASE_URL="https://api.example.edu")
    def test_api_url_can_be_pinned_in_settings(self):
        self.create("claude")
        self.assertContains(self.client.get(CONNECT_URL), "https://api.example.edu/api/v1/health/")

    # -- entry points -------------------------------------------------------

    def test_dashboard_has_the_create_button_for_admins(self):
        self.assertContains(self.client.get("/admin/"), "Create MCP token")

    def test_dashboard_hides_the_button_from_other_staff(self):
        self.client.force_login(self.editor)
        self.assertNotContains(self.client.get("/admin/"), "Create MCP token")

    def test_token_list_links_to_the_page(self):
        response = self.client.get(reverse("admin:authtoken_tokenproxy_changelist"))
        self.assertContains(response, "Connect an AI agent")
