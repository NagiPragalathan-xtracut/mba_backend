"""
Admin dashboard.

Unfold calls `dashboard_callback` with the admin index context and renders
whatever we add to it through `templates/admin/index.html`. The goal is a
landing page an editor can act on: what exists, what is still a draft, and
what changed recently.
"""

import logging

from django.urls import reverse

logger = logging.getLogger(__name__)


def _stat_card(title: str, icon: str, model, app_label: str, model_name: str, live_filter: dict) -> dict:
    """Build one counter card for ``model``.

    ``live_filter`` is what "publicly visible" means for that model -
    ``is_published`` for content, ``is_active`` for taxonomies.
    """
    total = model.objects.count()
    published = model.objects.filter(**live_filter).count()
    return {
        "title": title,
        "icon": icon,
        "total": total,
        "published": published,
        "hidden": total - published,
        "url": reverse(f"admin:{app_label}_{model_name}_changelist"),
        "add_url": reverse(f"admin:{app_label}_{model_name}_add"),
    }


def _content_stats():
    """Per-model counts. Imported lazily so the app registry is ready."""
    from apps.blogs.models import Blog
    from apps.core.models import Department
    from apps.events.models import Event
    from apps.faculty.models import Faculty

    published = {"is_published": True}
    return [
        _stat_card("Events", "event", Event, "events", "event", published),
        _stat_card("Blogs", "article", Blog, "blogs", "blog", published),
        _stat_card("Faculty", "groups", Faculty, "faculty", "faculty", published),
        _stat_card("Departments", "account_tree", Department, "core", "department", {"is_active": True}),
    ]


def _recent_activity(limit: int = 8):
    """The most recently edited content across all three apps, newest first."""
    from apps.blogs.models import Blog
    from apps.events.models import Event
    from apps.faculty.models import Faculty

    entries = []
    for model, label, url_name in (
        (Event, "Event", "admin:events_event_change"),
        (Blog, "Blog", "admin:blogs_blog_change"),
        (Faculty, "Faculty", "admin:faculty_faculty_change"),
    ):
        # Fetch `limit` from each model, then merge - the newest overall could
        # all come from a single app.
        for obj in model.objects.order_by("-updated_at")[:limit]:
            entries.append(
                {
                    "label": label,
                    "title": str(obj),
                    "updated_at": obj.updated_at,
                    "is_published": obj.is_published,
                    "url": reverse(url_name, args=[obj.pk]),
                }
            )

    entries.sort(key=lambda entry: entry["updated_at"], reverse=True)
    return entries[:limit]


def dashboard_callback(request, context):
    """Inject dashboard data into the admin index context."""
    try:
        context.update(
            {
                "stats": _content_stats(),
                "recent_activity": _recent_activity(),
                "quick_links": [
                    {"title": "API documentation", "icon": "api", "url": "/api/docs/"},
                    {"title": "OpenAPI schema", "icon": "data_object", "url": "/api/schema/"},
                    {"title": "API tokens", "icon": "key", "url": reverse("admin:authtoken_tokenproxy_changelist")},
                ],
            }
        )
    except Exception:  # noqa: BLE001
        # A broken dashboard widget must never take the whole admin down -
        # log it and fall back to an empty (but rendering) page.
        logger.exception("Failed to build admin dashboard context")
        context.setdefault("stats", [])
        context.setdefault("recent_activity", [])
        context.setdefault("quick_links", [])
    return context
