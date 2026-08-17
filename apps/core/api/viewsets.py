"""
Shared ViewSet behaviour for the content apps.

Two things every content endpoint needs and should not re-implement:

* **Visibility** - anonymous callers only ever see published rows; an
  authenticated editor (or the MCP server) sees drafts too.
* **Flexible lookup** - the same detail URL accepts a slug, a numeric id or a
  UUID, so an API client never has to translate between identifier styles.
"""

import uuid

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets


class FlexibleLookupMixin:
    """Resolve detail routes by slug, primary key or `unique_id`."""

    # A slug can contain digits, so try the cheapest unambiguous forms first.
    lookup_field = "slug"
    lookup_value_regex = "[^/]+"

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        value = self.kwargs[self.lookup_field]

        lookup = Q(slug=value)
        if value.isdigit():
            lookup |= Q(pk=int(value))
        try:
            lookup |= Q(unique_id=uuid.UUID(str(value)))
        except (ValueError, AttributeError, TypeError):
            pass  # not a UUID - slug/pk lookups still apply

        obj = get_object_or_404(queryset, lookup)
        self.check_object_permissions(self.request, obj)
        return obj


class PublishedVisibilityMixin:
    """Hide unpublished rows from anonymous callers."""

    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, "user", None)
        if user is None or not user.is_authenticated:
            return queryset.filter(is_published=True)
        return queryset


class BaseContentViewSet(FlexibleLookupMixin, PublishedVisibilityMixin, viewsets.ModelViewSet):
    """Base for the Event / Blog / Faculty viewsets."""

    ordering = ["display_order", "-created_at"]

    def get_serializer_class(self):
        """Use the light list serializer for collections when one is defined."""
        if self.action == "list" and getattr(self, "list_serializer_class", None):
            return self.list_serializer_class
        return super().get_serializer_class()


class TaxonomyViewSet(viewsets.ModelViewSet):
    """Base for the small lookup tables (departments, categories, designations)."""

    lookup_field = "slug"
    lookup_value_regex = "[^/]+"
    search_fields = ["name", "description"]
    ordering_fields = ["display_order", "name", "created_at"]
    ordering = ["display_order", "name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, "user", None)
        if user is None or not user.is_authenticated:
            return queryset.filter(is_active=True)
        return queryset
