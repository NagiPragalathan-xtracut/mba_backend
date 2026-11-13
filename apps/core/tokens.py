"""
API tokens for agents (the MCP server and other API clients).

One place decides how a token is issued, so `manage.py create_api_token` and
the admin's "Connect an AI agent" page behave identically:

* an agent gets its own user with no usable password - it can act only through
  its token and can never log in to the admin;
* rotating deletes the old token first, so the old key stops working at once.
"""

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.db import transaction
from django.utils.text import slugify
from rest_framework.authtoken.models import Token

AGENT_USERNAME_PREFIX = "mcp-"


class TokenIssueError(Exception):
    """The token could not be issued. The message is safe to show a user."""


@dataclass(frozen=True)
class IssuedToken:
    token: Token
    user_created: bool
    rotated: bool


def agent_username(name: str) -> str:
    """Turn a free-text agent name into its account's username.

    "Claude Desktop (office)" becomes "mcp-claude-desktop-office". Names that
    already carry the prefix are kept, so "mcp-bot" stays "mcp-bot". Returns an
    empty string when the name has no usable characters.
    """
    slug = slugify(name)
    if not slug:
        return ""
    return slug if slug.startswith(AGENT_USERNAME_PREFIX) else f"{AGENT_USERNAME_PREFIX}{slug}"


def is_agent_account(user) -> bool:
    """Agent accounts are the ones nobody can log in to with a password."""
    return not user.has_usable_password()


def agent_tokens():
    """Tokens that belong to agent accounts, newest first."""
    return (
        Token.objects.select_related("user")
        .filter(user__password__startswith=UNUSABLE_PASSWORD_PREFIX)
        .order_by("-created")
    )


@transaction.atomic
def issue_token(
    username: str,
    *,
    create_user: bool = False,
    rotate: bool = False,
    agents_only: bool = False,
) -> IssuedToken:
    """Return the token for ``username``, creating the user or token as needed.

    ``create_user`` creates a missing user as a token-only staff account.
    ``rotate`` revokes any existing token and issues a fresh key.
    ``agents_only`` refuses to touch accounts a person logs in with, so a
    token page can never rotate a human's key by picking their username.
    """
    User = get_user_model()
    user_created = False

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        if not create_user:
            raise TokenIssueError(
                f"No user named '{username}'. Re-run with --create-user to create one, "
                f"or use an existing username."
            ) from None
        # No password means Django stores an unusable one: token-only access.
        user = User.objects.create_user(username=username, password=None, is_staff=True)
        user_created = True
    else:
        if agents_only and not is_agent_account(user):
            raise TokenIssueError(f"'{username}' is a person's login, not an agent account.")

    rotated = False
    if rotate:
        deleted, _ = Token.objects.filter(user=user).delete()
        rotated = bool(deleted)

    token, _ = Token.objects.get_or_create(user=user)
    return IssuedToken(token=token, user_created=user_created, rotated=rotated)
