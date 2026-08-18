"""
The common content feed behind the website's News & Events page.

Events and blogs are stored separately - they have genuinely different fields
(an event has a date, a venue and a photo gallery; a post has an author, a read
time and a single cover image). The website, however, shows them side by side
on one page and needs them in **one shape**: the same card markup, the same
category chip, the same "Read More" link.

This module is that shared layer. :class:`FeedItem` normalises either model
into a single UI-ready record, so the frontend consumes one endpoint and never
branches on which table a row came from.

Routes (all read-only and public):

===============================  ==============================================
``/news-events/``                Merged, filterable, paginated feed
``/news-events/<slug>/``         One item, from either source
``/news-events/categories/``     Merged sidebar category list
===============================  ==============================================

Writes still go through the dedicated ``/events/`` and ``/blogs/`` endpoints,
which is where the validation and permissions live.
"""

from dataclasses import asdict, dataclass, field
from itertools import chain

from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.blogs.models import Blog, BlogCategory
from apps.core.models import Course
from apps.core.api.pagination import StandardResultsPagination
from apps.core.utils import dotted_date, html_paragraphs, long_date, short_date
from apps.events.models import Event, EventCategory

#: Discriminator values carried on every feed item.
TYPE_EVENT = "event"
TYPE_BLOG = "blog"

#: Where the website publishes each kind of item. Kept here rather than in the
#: frontend so a routing change is a one-line backend edit.
DETAIL_PATHS = {
    TYPE_EVENT: "/news-events/{slug}",
    TYPE_BLOG: "/news-events/blog/{slug}",
}


@dataclass
class FeedItem:
    """
    One entry in the merged feed, in exactly the shape the website renders.

    Every value is pre-formatted server-side. The frontend does no date
    arithmetic, no HTML parsing and no category lookups - it maps fields onto
    markup, which keeps the two codebases from drifting apart.
    """

    id: int
    type: str
    slug: str
    title: str
    excerpt: str
    image: str
    category: str
    category_slug: str
    #: Short badge date, e.g. "18 Dec".
    date: str
    #: Long date used on blog cards, e.g. "15 Jan 2025".
    date_long: str
    #: Dotted date on the detail page, e.g. "18.12.2024".
    date_label: str
    #: ISO date for sorting and ``<time>`` elements.
    date_iso: str
    #: "10:00 AM - 11:00 AM"; empty for anything without a start time.
    timing: str
    venue: str
    author: str
    reading_time_minutes: int
    #: Body text split into plain-text paragraphs.
    paragraphs: list[str] = field(default_factory=list)
    #: The original rich text, for callers that would rather render HTML.
    content_html: str = ""
    #: Extra photos beyond the cover image.
    gallery: list[dict] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    #: Programme names this entry relates to, for the Courses filter.
    courses: list[str] = field(default_factory=list)
    course_slugs: list[str] = field(default_factory=list)
    href: str = ""
    is_featured: bool = False
    display_order: int = 0
    seo: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def _absolute(request, url: str) -> str:
    """Expand a media path into an absolute URL the frontend can load."""
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return request.build_absolute_uri(url) if request else url


def _seo_payload(obj) -> dict:
    """The SEO field set, flattened for the frontend's ``generateMetadata``."""
    return {
        "meta_title": obj.meta_title,
        "meta_description": obj.meta_description,
        "keywords": obj.keywords,
        "canonical_url": obj.canonical_url,
        "robots": obj.robots,
        "og_title": obj.og_title,
        "og_description": obj.og_description,
        "og_image": obj.og_image,
        "twitter_card": obj.twitter_card,
        "twitter_title": obj.twitter_title,
        "twitter_description": obj.twitter_description,
        "twitter_image": obj.twitter_image,
        "schema_json": obj.schema_json,
    }


def event_to_feed_item(event: Event, request=None) -> FeedItem:
    """Normalise an :class:`~apps.events.models.Event` into a feed entry."""
    featured = event.featured_image
    gallery = [
        {
            "image": _absolute(request, image.image.url if image.image else ""),
            "alt": image.alt,
            "caption": image.caption,
        }
        for image in event.images.all()
        # The cover image is already carried in `image`; repeating it would
        # duplicate the first photo in every gallery strip.
        if image is not featured and image.image
    ]

    return FeedItem(
        id=event.pk,
        type=TYPE_EVENT,
        slug=event.slug,
        title=event.title,
        excerpt=event.summary,
        image=_absolute(request, event.featured_image_url),
        category=event.category.name if event.category_id else "",
        category_slug=event.category.slug if event.category_id else "",
        date=short_date(event.event_date),
        date_long=long_date(event.event_date),
        date_label=dotted_date(event.event_date),
        date_iso=event.event_date.isoformat() if event.event_date else "",
        timing=event.timing_label,
        venue=event.venue,
        author=event.author,
        reading_time_minutes=0,
        paragraphs=html_paragraphs(event.content),
        content_html=event.content,
        gallery=gallery,
        departments=[department.name for department in event.departments.all()],
        courses=[course.name for course in event.courses.all()],
        course_slugs=[course.slug for course in event.courses.all()],
        href=DETAIL_PATHS[TYPE_EVENT].format(slug=event.slug),
        is_featured=event.is_featured,
        display_order=event.display_order,
        seo=_seo_payload(event),
    )


def blog_to_feed_item(blog: Blog, request=None) -> FeedItem:
    """Normalise a :class:`~apps.blogs.models.Blog` into a feed entry."""
    # A post can sit in several categories but a card shows one chip, so the
    # first (lowest display_order) category is the one the website labels it by.
    categories = list(blog.categories.all())
    primary = categories[0] if categories else None

    return FeedItem(
        id=blog.pk,
        type=TYPE_BLOG,
        slug=blog.slug,
        title=blog.title,
        excerpt=blog.summary,
        image=_absolute(request, blog.featured_image_url),
        category=primary.name if primary else "",
        category_slug=primary.slug if primary else "",
        date=short_date(blog.published_date),
        date_long=long_date(blog.published_date),
        date_label=dotted_date(blog.published_date),
        date_iso=blog.published_date.isoformat() if blog.published_date else "",
        timing="",
        venue="",
        author=blog.author_name or blog.author,
        reading_time_minutes=blog.reading_time_minutes,
        paragraphs=html_paragraphs(blog.content),
        content_html=blog.content,
        gallery=[
            {
                "image": _absolute(request, image.image.url if image.image else ""),
                "alt": image.alt,
                "caption": image.caption,
            }
            for image in blog.images.all()
            if image.image
        ],
        departments=[department.name for department in blog.departments.all()],
        courses=[course.name for course in blog.courses.all()],
        course_slugs=[course.slug for course in blog.courses.all()],
        href=DETAIL_PATHS[TYPE_BLOG].format(slug=blog.slug),
        is_featured=blog.is_featured,
        display_order=blog.display_order,
        seo=_seo_payload(blog),
    )


# ---------------------------------------------------------------------------
# Query building
# ---------------------------------------------------------------------------


def _visible(queryset, request):
    """Anonymous callers see published rows only; editors also see drafts."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return queryset.filter(is_published=True)
    return queryset


def _event_queryset(request):
    return _visible(
        Event.objects.select_related("category").prefetch_related("departments", "courses", "images"),
        request,
    )


def _blog_queryset(request):
    return _visible(
        Blog.objects.prefetch_related("categories", "departments", "courses", "images"),
        request,
    )


def _apply_common_filters(request, events, blogs):
    """
    Apply the query parameters both models understand.

    Anything a model cannot express is skipped for that model rather than
    raising, so ``?category=leadership`` narrows the blogs and simply matches
    no events instead of failing the whole request.
    """
    params = request.query_params

    category = params.get("category", "").strip()
    if category and category.lower() != "all":
        events = events.filter(category__slug__iexact=category)
        blogs = blogs.filter(categories__slug__iexact=category).distinct()

    department = params.get("department", "").strip()
    if department:
        events = events.filter(departments__slug__iexact=department).distinct()
        blogs = blogs.filter(departments__slug__iexact=department).distinct()

    course = params.get("course", "").strip()
    if course and course.lower() != "all":
        events = events.filter(courses__slug__iexact=course).distinct()
        blogs = blogs.filter(courses__slug__iexact=course).distinct()

    search = params.get("search", "").strip()
    if search:
        events = events.filter(title__icontains=search)
        blogs = blogs.filter(title__icontains=search)

    featured = params.get("featured", "").strip().lower()
    if featured in {"true", "1", "yes"}:
        events = events.filter(is_featured=True)
        blogs = blogs.filter(is_featured=True)

    date_from = parse_date(params.get("date_from", "") or "")
    if date_from:
        events = events.filter(event_date__gte=date_from)
        blogs = blogs.filter(published_date__gte=date_from)

    date_to = parse_date(params.get("date_to", "") or "")
    if date_to:
        events = events.filter(event_date__lte=date_to)
        blogs = blogs.filter(published_date__lte=date_to)

    return events, blogs


def _sort_key(item: FeedItem):
    """
    Editor order first, then newest.

    The two models cannot be ordered by the database together, so the merge is
    sorted in Python. An item with no date sorts last within its rank rather
    than crashing the comparison.
    """
    return (item.display_order, item.date_iso == "", _negated_iso(item.date_iso))


def _negated_iso(value: str) -> str:
    """Sort ISO dates descending inside an ascending ``sorted()``."""
    # Inverting each digit turns a lexicographic ascending sort into a
    # descending one without needing a reverse pass per key.
    return "".join(str(9 - int(char)) if char.isdigit() else char for char in value)


def build_feed(request, types=None) -> list[FeedItem]:
    """Merged, filtered, ordered feed items for the current request."""
    types = types or {TYPE_EVENT, TYPE_BLOG}
    events, blogs = _apply_common_filters(request, _event_queryset(request), _blog_queryset(request))

    items = chain(
        (event_to_feed_item(event, request) for event in events) if TYPE_EVENT in types else (),
        (blog_to_feed_item(blog, request) for blog in blogs) if TYPE_BLOG in types else (),
    )
    return sorted(items, key=_sort_key)


# ---------------------------------------------------------------------------
# Serializers - declared for the OpenAPI schema only; the views return dicts
# assembled by FeedItem, which is already in its final shape.
# ---------------------------------------------------------------------------


class FeedItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    type = serializers.ChoiceField(choices=[TYPE_EVENT, TYPE_BLOG], read_only=True)
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    excerpt = serializers.CharField(read_only=True)
    image = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    category_slug = serializers.CharField(read_only=True)
    date = serializers.CharField(read_only=True)
    date_long = serializers.CharField(read_only=True)
    date_label = serializers.CharField(read_only=True)
    date_iso = serializers.CharField(read_only=True)
    timing = serializers.CharField(read_only=True)
    venue = serializers.CharField(read_only=True)
    author = serializers.CharField(read_only=True)
    reading_time_minutes = serializers.IntegerField(read_only=True)
    paragraphs = serializers.ListField(child=serializers.CharField(), read_only=True)
    content_html = serializers.CharField(read_only=True)
    gallery = serializers.ListField(child=serializers.DictField(), read_only=True)
    departments = serializers.ListField(child=serializers.CharField(), read_only=True)
    courses = serializers.ListField(child=serializers.CharField(), read_only=True)
    course_slugs = serializers.ListField(child=serializers.CharField(), read_only=True)
    href = serializers.CharField(read_only=True)
    is_featured = serializers.BooleanField(read_only=True)
    display_order = serializers.IntegerField(read_only=True)
    seo = serializers.DictField(read_only=True)


class FeedCategorySerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    #: Which tables the slug appears in - a name such as "Campus Life" is a
    #: valid category for both an event and a post.
    sources = serializers.ListField(child=serializers.CharField(), read_only=True)
    count = serializers.IntegerField(read_only=True)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


@extend_schema(
    summary="Merged news, events and blogs feed",
    description=(
        "One listing covering both events and blog posts in a single, UI-ready "
        "shape. Filter with `type=event|blog`, `category`, `department`, `course`, "
        "`search`, `featured`, `date_from` and `date_to`."
    ),
    parameters=[
        OpenApiParameter("type", str, description="`event`, `blog`, or omit for both."),
        OpenApiParameter("category", str, description="Category slug. `all` is treated as no filter."),
        OpenApiParameter("department", str, description="Department slug."),
        OpenApiParameter("course", str, description="Course slug. `all` is treated as no filter."),
        OpenApiParameter("search", str, description="Case-insensitive title match."),
        OpenApiParameter("featured", bool, description="Only entries flagged as featured."),
        OpenApiParameter("date_from", str, description="ISO date lower bound."),
        OpenApiParameter("date_to", str, description="ISO date upper bound."),
        OpenApiParameter("page_size", int, description="Items per page (max 100)."),
    ],
    responses={200: FeedItemSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def news_events_feed(request):
    """The merged listing consumed by the website's News & Events page."""
    requested_type = request.query_params.get("type", "").strip().lower()
    if requested_type in {TYPE_EVENT, TYPE_BLOG}:
        types = {requested_type}
    elif requested_type:
        return Response(
            {"detail": f"Unknown type '{requested_type}'. Use '{TYPE_EVENT}', '{TYPE_BLOG}', or omit it."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    else:
        types = {TYPE_EVENT, TYPE_BLOG}

    items = [item.as_dict() for item in build_feed(request, types)]

    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(items, request)
    return paginator.get_paginated_response(page)


@extend_schema(
    summary="Retrieve one feed entry",
    description=(
        "Looks the identifier up as an event first, then as a blog post. "
        "Accepts a slug or a numeric id. Pass `type` to disambiguate when an "
        "event and a post share a slug."
    ),
    parameters=[OpenApiParameter("type", str, description="Restrict the lookup to `event` or `blog`.")],
    responses={200: FeedItemSerializer},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def news_events_detail(request, identifier):
    """One entry, whichever model it lives in."""
    requested_type = request.query_params.get("type", "").strip().lower()

    lookups = []
    if requested_type in {"", TYPE_EVENT}:
        lookups.append((TYPE_EVENT, _event_queryset(request), event_to_feed_item))
    if requested_type in {"", TYPE_BLOG}:
        lookups.append((TYPE_BLOG, _blog_queryset(request), blog_to_feed_item))

    if not lookups:
        return Response(
            {"detail": f"Unknown type '{requested_type}'. Use '{TYPE_EVENT}' or '{TYPE_BLOG}'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    for _, queryset, to_feed_item in lookups:
        obj = queryset.filter(slug=identifier).first()
        if obj is None and identifier.isdigit():
            obj = queryset.filter(pk=int(identifier)).first()
        if obj is not None:
            return Response(to_feed_item(obj, request).as_dict())

    return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="Merged category list",
    description=(
        "Event categories and blog categories in one list, de-duplicated by slug "
        "and carrying the number of published entries in each. Powers the sidebar "
        "filter on the News & Events page. Pass `type` to get just one side of it."
    ),
    parameters=[OpenApiParameter("type", str, description="Restrict to `event` or `blog` categories.")],
    responses={200: FeedCategorySerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def news_events_categories(request):
    """Categories from both models, merged for one sidebar."""
    requested_type = request.query_params.get("type", "").strip().lower()
    if requested_type and requested_type not in {TYPE_EVENT, TYPE_BLOG}:
        return Response(
            {"detail": f"Unknown type '{requested_type}'. Use '{TYPE_EVENT}', '{TYPE_BLOG}', or omit it."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    sources = []
    if requested_type in {"", TYPE_EVENT}:
        sources.append((TYPE_EVENT, EventCategory.objects.filter(is_active=True), "events"))
    if requested_type in {"", TYPE_BLOG}:
        sources.append((TYPE_BLOG, BlogCategory.objects.filter(is_active=True), "blogs"))

    # Merged on slug: "Campus Life" exists as both an event and a blog category,
    # and the sidebar must not show it twice. Counts add up across both.
    merged: dict[str, dict] = {}
    for source_type, queryset, related_name in sources:
        for category in queryset:
            entry = merged.setdefault(
                category.slug,
                {
                    "name": category.name,
                    "slug": category.slug,
                    "sources": [],
                    "count": 0,
                    "_order": category.display_order,
                },
            )
            entry["sources"].append(source_type)
            entry["count"] += getattr(category, related_name).filter(is_published=True).count()
            entry["_order"] = min(entry["_order"], category.display_order)

    ordered = sorted(merged.values(), key=lambda entry: (entry["_order"], entry["name"]))
    for entry in ordered:
        entry.pop("_order")
    return Response(ordered)


class FeedCourseSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    short_name = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


@extend_schema(
    summary="Course filter options",
    description=(
        "Active programmes with the number of published events and posts tagged "
        "to each. Powers the Courses filter on the News & Events page."
    ),
    responses={200: FeedCourseSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def news_events_courses(request):
    """Programmes offered as filter options on the News & Events page."""
    courses = [
        {
            "name": course.name,
            "slug": course.slug,
            "short_name": course.short_name,
            # Counted across both sources, matching what the filter returns.
            "count": (
                course.events.filter(is_published=True).count()
                + course.blogs.filter(is_published=True).count()
            ),
        }
        for course in Course.objects.filter(is_active=True)
    ]
    return Response(courses)
