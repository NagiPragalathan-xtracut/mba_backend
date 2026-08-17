"""Event tools: create, update, list and illustrate events and achievements."""

from mcp_server.client import MBUClient
from mcp_server.tools._common import as_paragraphs, compact, created, listing, split_csv, updated

LIST_KEYS = ("id", "title", "slug", "category", "departments", "event_date", "venue", "is_published", "display_order")
DETAIL_KEYS = (
    "id", "title", "slug", "summary", "category", "departments",
    "event_date", "end_date", "venue", "featured_image_url",
    "is_published", "is_featured", "display_order", "meta_title", "meta_description", "keywords",
)
IMAGE_KEYS = ("id", "alt", "caption", "is_featured", "display_order", "image_url")


def register(mcp, client: MBUClient) -> None:
    """Attach the event tools to the MCP server."""

    @mcp.tool()
    def list_events(
        category: str | None = None,
        department: str | None = None,
        search: str | None = None,
        year: int | None = None,
        page: int | None = None,
    ) -> dict:
        """List events, newest and highest-priority first.

        Args:
            category: Category slug, e.g. "upcoming" or "achievements".
            department: Department slug, e.g. "computer-science-engineering".
            search: Free-text search across title, summary, content and venue.
            year: Restrict to events whose date falls in this year.
            page: Page number (20 per page).
        """
        params = {"category": category, "department": department, "search": search, "year": year, "page": page}
        return listing(client.get("events/", params), LIST_KEYS)

    @mcp.tool()
    def get_event(identifier: str) -> dict:
        """Fetch one event in full, including its photo gallery.

        Args:
            identifier: The event's slug, numeric id or UUID.
        """
        result = client.get(f"events/{identifier}/")
        detail = compact(result, DETAIL_KEYS)
        detail["images"] = [compact(image, IMAGE_KEYS) for image in result.get("images", [])]
        return detail

    @mcp.tool()
    def create_event(
        title: str,
        category: str,
        content: str,
        departments: str | None = None,
        summary: str | None = None,
        event_date: str | None = None,
        end_date: str | None = None,
        venue: str | None = None,
        display_order: int | None = None,
        is_published: bool = True,
        is_featured: bool = False,
    ) -> dict:
        """Create an event or achievement.

        SEO metadata (meta title/description, Open Graph, Twitter card,
        schema.org JSON-LD) is generated automatically from what you pass -
        there is no need to supply it.

        The event's highlight photo is chosen from its gallery, so after
        creating the event call `upload_event_image` with `is_featured=True`
        (the first photo uploaded becomes the highlight automatically).

        Args:
            title: Event name, e.g. "National Tech Symposium 2026".
            category: Category slug from `list_event_categories`, e.g. "upcoming".
            content: Full description. Plain text is converted to HTML paragraphs;
                HTML is stored as given.
            departments: Comma-separated department slugs, e.g. "cse, ece".
                Leave empty for university-wide events.
            summary: Short teaser for listing cards. Derived from the content when omitted.
            event_date: Start date as YYYY-MM-DD.
            end_date: Last day for multi-day events, as YYYY-MM-DD. Must not precede event_date.
            venue: Where it takes place.
            display_order: Lower numbers appear first.
            is_published: Whether it is visible on the public website.
            is_featured: Whether to highlight it on listing pages.
        """
        payload = {
            "title": title,
            "category": category,
            "content": as_paragraphs(content),
            "departments": split_csv(departments),
            "summary": summary,
            "event_date": event_date,
            "end_date": end_date,
            "venue": venue,
            "display_order": display_order,
            "is_published": is_published,
            "is_featured": is_featured,
        }
        return created("event", client.post("events/", payload), DETAIL_KEYS)

    @mcp.tool()
    def update_event(
        identifier: str,
        title: str | None = None,
        category: str | None = None,
        content: str | None = None,
        departments: str | None = None,
        summary: str | None = None,
        event_date: str | None = None,
        end_date: str | None = None,
        venue: str | None = None,
        display_order: int | None = None,
        is_published: bool | None = None,
        is_featured: bool | None = None,
    ) -> dict:
        """Update an existing event. Only the arguments you pass are changed.

        Args:
            identifier: The event's slug, numeric id or UUID.
            title: New event name.
            category: New category slug.
            content: New description (plain text or HTML).
            departments: Comma-separated department slugs. Replaces the whole set.
            summary: New listing teaser.
            event_date: New start date, YYYY-MM-DD.
            end_date: New end date, YYYY-MM-DD.
            venue: New venue.
            display_order: New ordering weight.
            is_published: Publish or unpublish.
            is_featured: Feature or unfeature.
        """
        payload = {
            "title": title,
            "category": category,
            "content": as_paragraphs(content),
            "departments": split_csv(departments),
            "summary": summary,
            "event_date": event_date,
            "end_date": end_date,
            "venue": venue,
            "display_order": display_order,
            "is_published": is_published,
            "is_featured": is_featured,
        }
        return updated("event", client.patch(f"events/{identifier}/", payload), DETAIL_KEYS)

    @mcp.tool()
    def upload_event_image(
        identifier: str,
        image_path: str,
        alt: str | None = None,
        caption: str | None = None,
        is_featured: bool = False,
        display_order: int | None = None,
    ) -> dict:
        """Upload a photo into an event's gallery.

        The first photo uploaded for an event automatically becomes its
        highlight image. Passing `is_featured=True` promotes this photo and
        demotes the previous highlight.

        Args:
            identifier: The event's slug, numeric id or UUID.
            image_path: Absolute path to an image file on this machine
                (png, jpg, gif, webp, bmp, avif or svg).
            alt: Alt text for accessibility and SEO. Defaults to the event title.
            caption: Optional caption shown under the photo.
            is_featured: Make this the event's highlight image.
            display_order: Lower numbers appear first in the gallery.
        """
        fields = {
            "alt": alt,
            "caption": caption,
            "is_featured": "true" if is_featured else "false",
            "display_order": display_order,
        }
        result = client.upload(f"events/{identifier}/images/", image_path, fields)
        return created("event_image", result, IMAGE_KEYS)

    @mcp.tool()
    def set_event_featured_image(image_id: int) -> dict:
        """Promote an already-uploaded gallery photo to the event's highlight image.

        Use `get_event` to see the gallery and its image ids.

        Args:
            image_id: Numeric id of the gallery photo.
        """
        return updated("event_image", client.post(f"event-images/{image_id}/set-featured/", {}), IMAGE_KEYS)

    @mcp.tool()
    def delete_event(identifier: str) -> dict:
        """Permanently delete an event and its gallery photos.

        This cannot be undone. To hide an event instead, call `update_event`
        with `is_published=False`.

        Args:
            identifier: The event's slug, numeric id or UUID.
        """
        client.delete(f"events/{identifier}/")
        return {"status": "deleted", "type": "event", "identifier": identifier}
