"""
Re-register third-party admins with Unfold styling.

Django's own `User`/`Group` admins and DRF's token admin are registered by
their packages against the stock `django.contrib.admin.ModelAdmin`. Inside the
Unfold theme those pages render with unstyled widgets - the related-field
"edit / add / view" controls in particular collapse into a stack of raw icons.

Re-registering them against `unfold.admin.ModelAdmin` gives them the same
look as the rest of the dashboard. The upstream admin classes are kept as base
classes so their behaviour (password handling, permission editing) is
unchanged.

This module is imported from `apps/core/admin/__init__.py`. `apps.core` is
listed after `django.contrib.*` and `rest_framework.authtoken` in
INSTALLED_APPS, so those admins are already registered when this runs.
"""

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm


def _unregister(model) -> None:
    """Unregister a model, tolerating it not being registered."""
    try:
        admin.site.unregister(model)
    except NotRegistered:
        # The upstream package may not be installed, or ordering may have
        # changed - either way there is nothing to replace.
        pass


_unregister(User)
_unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Django's user admin, themed by Unfold."""

    # Unfold's versions of these render the password widgets correctly.
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ["username", "email", "full_name", "is_staff", "access_badge"]
    list_filter = ["is_staff", "is_superuser", "is_active", "groups"]
    compressed_fields = True

    @display(description="Name")
    def full_name(self, obj):
        return obj.get_full_name() or "—"

    @display(
        description="Access",
        label={"Superuser": "danger", "Staff": "info", "Active": "success", "Disabled": "warning"},
    )
    def access_badge(self, obj):
        if not obj.is_active:
            return "Disabled"
        if obj.is_superuser:
            return "Superuser"
        return "Staff" if obj.is_staff else "Active"


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    """Django's group admin, themed by Unfold."""

    list_display = ["name", "member_count", "permission_count"]
    compressed_fields = True

    @display(description="Members")
    def member_count(self, obj):
        return obj.user_set.count()

    @display(description="Permissions")
    def permission_count(self, obj):
        return obj.permissions.count()


# ---------------------------------------------------------------------------
# DRF authentication tokens
# ---------------------------------------------------------------------------

try:
    from rest_framework.authtoken.models import TokenProxy
except ImportError:  # pragma: no cover - authtoken is a hard dependency here
    TokenProxy = None

if TokenProxy is not None:
    _unregister(TokenProxy)

    @admin.register(TokenProxy)
    class TokenAdmin(ModelAdmin):
        """
        API tokens, themed by Unfold.

        The key is generated on save and never editable - rotating a token
        means deleting this row and issuing a new one, which is what
        `manage.py create_api_token --rotate` does.
        """

        list_display = ["masked_key", "user", "created"]
        search_fields = ["user__username", "user__email"]
        list_filter = ["created"]
        ordering = ["-created"]
        # Autocomplete rather than the raw related widget - that widget is the
        # one that renders as a stack of unstyled icons.
        autocomplete_fields = ["user"]
        readonly_fields = ["key", "created"]
        compressed_fields = True

        fieldsets = (
            (
                None,
                {
                    "fields": ("user",),
                    "description": (
                        "Tokens authenticate API clients such as the MCP server. "
                        "The key is generated automatically when you save."
                    ),
                },
            ),
            ("Token", {"fields": ("key", "created")}),
        )

        def get_fieldsets(self, request, obj=None):
            # A new token has no key or timestamp yet, so hide that section.
            if obj is None:
                return ((None, {"fields": ("user",)}),)
            return super().get_fieldsets(request, obj)

        @display(description="Key")
        def masked_key(self, obj):
            """Show only the last characters - the full key is a credential."""
            key = obj.key or ""
            return f"…{key[-8:]}" if len(key) > 8 else key
