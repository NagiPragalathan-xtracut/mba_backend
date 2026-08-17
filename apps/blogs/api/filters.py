"""Query filters for the blogs API."""

import django_filters

from apps.blogs.models import Blog


class BlogFilter(django_filters.FilterSet):
    """Slug-based filters mirroring the website's blog listing controls."""

    category = django_filters.CharFilter(field_name="categories__slug", lookup_expr="iexact", distinct=True)
    department = django_filters.CharFilter(field_name="departments__slug", lookup_expr="iexact", distinct=True)
    author = django_filters.CharFilter(field_name="author_name", lookup_expr="icontains")
    date_from = django_filters.DateFilter(field_name="published_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="published_date", lookup_expr="lte")
    year = django_filters.NumberFilter(field_name="published_date__year")

    class Meta:
        model = Blog
        fields = ["category", "department", "author", "is_featured", "is_published", "date_from", "date_to", "year"]
