"""
"Connect an AI agent" - issue an MCP token from the admin and hand over a
prompt that lets the agent install and configure the MCP server by itself.

Mounted under the API token admin (/admin/authtoken/tokenproxy/connect/) by
`third_party.TokenAdmin.get_urls`, so it inherits the admin's login, CSRF and
never-cache handling.

After a POST the page redirects (post/redirect/get) and remembers only the
agent's *username* in the session; the key itself is read back from the token
table when the page renders, so no credential is copied into the session.
"""

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView
from rest_framework.authtoken.models import Token
from unfold.views import UnfoldModelAdminViewMixin

from apps.core.agent_setup import INSTALL_DIR_POSIX, SERVER_NAME, AgentSetup
from apps.core.tokens import TokenIssueError, agent_tokens, agent_username, is_agent_account, issue_token

URL_NAME = "authtoken_tokenproxy_connect"
SESSION_KEY = "connect_agent_username"


def required_permissions() -> tuple[str, ...]:
    """Creating an agent creates a user *and* a token, so both are needed."""
    opts = get_user_model()._meta
    return ("authtoken.add_tokenproxy", f"{opts.app_label}.add_{opts.model_name}")


def can_connect_agent(user) -> bool:
    return bool(user.is_active and user.is_staff and user.has_perms(required_permissions()))


def sidebar_visible(request) -> bool:
    """Unfold sidebar permission callback (referenced by dotted path in settings)."""
    return can_connect_agent(request.user)


def connect_agent_url() -> str:
    return reverse(f"admin:{URL_NAME}")


class ConnectAgentForm(forms.Form):
    name = forms.CharField(
        label="Agent name",
        max_length=40,
        help_text="Who or what will use it, e.g. “Claude Desktop – office”. Saved as an mcp-… account.",
        widget=forms.TextInput(attrs={"placeholder": "claude-desktop-office", "autocomplete": "off"}),
    )
    replace = forms.BooleanField(
        label="Replace the token if this agent already exists",
        required=False,
        help_text="The old token stops working immediately.",
    )

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        if not name:
            return cleaned

        username = agent_username(name)
        if not username:
            self.add_error("name", "Use at least one letter or number.")
            return cleaned

        user = get_user_model().objects.filter(username=username).first()
        if user is not None:
            if not is_agent_account(user):
                self.add_error("name", f"“{username}” is a person's login, not an agent. Choose another name.")
            elif Token.objects.filter(user=user).exists() and not cleaned.get("replace"):
                self.add_error(
                    "name",
                    f"“{username}” already has a token. Use “Setup prompt” in the list below to see it "
                    f"again, or tick “Replace” to issue a new one.",
                )

        cleaned["username"] = username
        return cleaned


class ConnectAgentView(UnfoldModelAdminViewMixin, FormView):
    title = "Connect an AI agent"
    template_name = "admin/connect_agent.html"
    form_class = ConnectAgentForm

    def get_permission_required(self):
        return required_permissions()

    # -- actions -----------------------------------------------------------

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "show":
            return self._show_existing(request.POST.get("username", ""))
        if action == "revoke":
            return self._revoke(request.POST.get("username", ""))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        username = form.cleaned_data["username"]
        try:
            issued = issue_token(
                username,
                create_user=True,
                rotate=form.cleaned_data["replace"],
                agents_only=True,
            )
        except TokenIssueError as exc:
            form.add_error("name", str(exc))
            return self.form_invalid(form)

        if issued.rotated:
            messages.warning(self.request, f"New token issued for “{username}”. The old one no longer works.")
        else:
            messages.success(self.request, f"Token created for “{username}”.")

        self.request.session[SESSION_KEY] = username
        return redirect(connect_agent_url())

    def _show_existing(self, username: str):
        token = agent_tokens().filter(user__username=username).first()
        if token is None:
            messages.error(self.request, "That agent no longer has a token.")
        else:
            self.request.session[SESSION_KEY] = username
        return redirect(connect_agent_url())

    def _revoke(self, username: str):
        # Handled here rather than by linking to the stock delete page: that
        # page's URL is built from the token key, which would leak the key
        # into the address bar, browser history and server logs.
        if not self.request.user.has_perm("authtoken.delete_tokenproxy"):
            raise PermissionDenied
        deleted, _ = agent_tokens().filter(user__username=username).delete()
        if deleted:
            messages.success(self.request, f"Token for “{username}” revoked. That agent can no longer make changes.")
        else:
            messages.error(self.request, "That agent no longer has a token.")
        return redirect(connect_agent_url())

    # -- rendering ---------------------------------------------------------

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "result": self._pop_result(),
                "connections": self._connections(),
                "api_base_url": self._api_base_url(),
                "server_name": SERVER_NAME,
                "install_dir": INSTALL_DIR_POSIX,
                "tokens_url": reverse("admin:authtoken_tokenproxy_changelist"),
            }
        )
        return context

    def _api_base_url(self) -> str:
        return settings.AGENT_SETUP_API_BASE_URL or self.request.build_absolute_uri("/").rstrip("/")

    def _pop_result(self):
        """The agent created or picked on the previous request, shown once."""
        username = self.request.session.pop(SESSION_KEY, None)
        if not username:
            return None
        token = agent_tokens().filter(user__username=username).first()
        if token is None:
            return None

        setup = AgentSetup(
            site_name=settings.SITE_NAME,
            api_base_url=self._api_base_url(),
            token=token.key,
            username=username,
            repo_url=settings.AGENT_SETUP_REPO_URL,
            repo_branch=settings.AGENT_SETUP_REPO_BRANCH,
        )
        return {
            "username": username,
            "key": token.key,
            "prompt": setup.prompt(),
            "client_config": setup.client_config(),
            "env_file": setup.env_file(),
            "health_url": setup.health_url,
        }

    def _connections(self):
        return [
            {
                "username": token.user.get_username(),
                "masked_key": f"…{token.key[-8:]}",
                "created": token.created,
            }
            for token in agent_tokens()
        ]
