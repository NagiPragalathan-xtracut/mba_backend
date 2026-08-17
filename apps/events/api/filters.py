"""Query filters for the events API."""

import django_filters

from apps.events.models import Event


class EventFilter(django_filters.FilterSet):
    """
    Filters the website's events page needs.

    Slug-based rather than id-based so a frontend route like
    ``/events?department=cse&category=upcoming`` maps straight onto the query.
    """

    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="iexact")
    department = django_filters.CharFilter(field_name="departments__slug", lookup_expr="iexact", distinct=True)
    date_from = django_filters.DateFilter(field_name="event_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="event_date", lookup_expr="lte")
    year = django_filters.NumberFilter(field_name="event_date__year")

    class Meta:
        model = Event
        fields = ["category", "department", "is_featured", "is_published", "date_from", "date_to", "year"]
