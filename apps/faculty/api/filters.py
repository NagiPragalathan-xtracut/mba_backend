"""Query filters for the faculty API."""

import django_filters

from apps.faculty.models import Faculty


class FacultyFilter(django_filters.FilterSet):
    """Slug-based filters for the faculty directory."""

    department = django_filters.CharFilter(field_name="departments__slug", lookup_expr="iexact", distinct=True)
    designation = django_filters.CharFilter(field_name="designation__slug", lookup_expr="iexact")
    qualification = django_filters.CharFilter(field_name="qualification", lookup_expr="icontains")
    has_email = django_filters.BooleanFilter(method="filter_has_email", label="Has a public email address")

    class Meta:
        model = Faculty
        fields = ["department", "designation", "qualification", "has_email", "is_featured", "is_published"]

    def filter_has_email(self, queryset, name, value):
        """`has_email=true` keeps only profiles with a contact address."""
        if value is None:
            return queryset
        return queryset.exclude(mail_id="") if value else queryset.filter(mail_id="")
