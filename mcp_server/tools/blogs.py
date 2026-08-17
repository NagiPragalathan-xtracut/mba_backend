"""Blog tools: create, update, list and illustrate blog posts."""

from mcp_server.client import MBUClient
from mcp_server.tools._common import as_paragraphs, compact, created, listing, split_csv, updated

LIST_KEYS = (
    "id", "title", "slug", "categories", "departments", "author_name",
    "published_date", "reading_time_minutes", "is_published", "display_order",
)
DETAIL_KEYS = (
    "id", "title", "slug", "summary", "categories", "departments",
    "author_name", "published_date", "reading_time_minutes", "featured_image_url",
    "is_published", "is_featured", "display_order", "meta_title", "meta_description", "keywords",
)
IMAGE_KEYS = ("id", "alt", "caption", "display_order", "image_url")


def register(mcp, client: MBUClient) -> None:
    """Attach the blog tools to the MCP server."""

    @mcp.tool()
    def list_blogs(
        category: str | None = None,
        department: str | None = None,
        author: str | None = None,
        search: str | None = None,
        year: int | None = None,
        page: int | None = None,
    ) -> dict:
        """List blog posts, newest first.

        Args:
            category: Category slug, e.g. "research".
            department: Department slug, e.g. "computer-science-engineering".
            author: Partial author name match.
            search: Free-text search across title, summary, content and author.
            year: Restrict to posts published in this year.
            page: Page number (20 per page).
        """
        params = {
            "category": category, "department": department, "author": author,
            "search": search, "year": year, "page": page,
        }
        return listing(client.get("blogs/", params), LIST_KEYS)

    @mcp.tool()
    def get_blog(identifier: str) -> dict:
        """Fetch one blog post in full, including its image gallery.

        Args:
            identifier: The post's slug, numeric id or UUID.
        """
        result = client.get(f"blogs/{identifier}/")
        detail = compact(result, DETAIL_KEYS)
        detail["images"] = [compact(image, IMAGE_KEYS) for image in result.get("images", [])]
        return detail

    @mcp.tool()
    def create_blog(
        title: str,
        content: str,
        categories: str | None = None,
        departments: str | None = None,
        summary: str | None = None,
        author_name: str | None = None,
        published_date: str | None = None,
        display_order: int | None = None,
        is_published: bool = True,
        is_featured: bool = False,
    ) -> dict:
        """Create a blog post.

        SEO metadata is generated automatically from the title, content and
        categories - do not supply it.

        A post's cover image is uploaded separately with
        `set_blog_cover_image`; extra in-article photos go through
        `upload_blog_image`.

        Args:
            title: Post headline.
            content: Article body. Plain text is converted to HTML paragraphs;
                HTML is stored as given.
            categories: Comma-separated category slugs from `list_blog_categories`.
            departments: Comma-separated department slugs. Leave empty for
                university-wide posts.
            summary: Listing teaser. Derived from the content when omitted.
            author_name: Byline shown on the post.
            published_date: Publication date as YYYY-MM-DD. Defaults to today.
            display_order: Lower numbers appear first.
            is_published: Whether it is visible on the public website.
            is_featured: Whether to highlight it on listing pages.
        """
        payload = {
            "title": title,
            "content": as_paragraphs(content),
            "categories": split_csv(categories),
            "departments": split_csv(departments),
            "summary": summary,
            "author_name": author_name,
            "published_date": published_date,
            "display_order": display_order,
            "is_published": is_published,
            "is_featured": is_featured,
        }
        return created("blog", client.post("blogs/", payload), DETAIL_KEYS)

    @mcp.tool()
    def update_blog(
        identifier: str,
        title: str | None = None,
        content: str | None = None,
        categories: str | None = None,
        departments: str | None = None,
        summary: str | None = None,
        author_name: str | None = None,
        published_date: str | None = None,
        display_order: int | None = None,
        is_published: bool | None = None,
        is_featured: bool | None = None,
    ) -> dict:
        """Update an existing blog post. Only the arguments you pass are changed.

        Args:
            identifier: The post's slug, numeric id or UUID.
            title: New headline.
            content: New body (plain text or HTML).
            categories: Comma-separated category slugs. Replaces the whole set.
            departments: Comma-separated department slugs. Replaces the whole set.
            summary: New listing teaser.
            author_name: New byline.
            published_date: New publication date, YYYY-MM-DD.
            display_order: New ordering weight.
            is_published: Publish or unpublish.
            is_featured: Feature or unfeature.
        """
        payload = {
            "title": title,
            "content": as_paragraphs(content),
            "categories": split_csv(categories),
            "departments": split_csv(departments),
            "summary": summary,
            "author_name": author_name,
            "published_date": published_date,
            "display_order": display_order,
            "is_published": is_published,
            "is_featured": is_featured,
        }
        return updated("blog", client.patch(f"blogs/{identifier}/", payload), DETAIL_KEYS)

    @mcp.tool()
    def set_blog_cover_image(identifier: str, image_path: str, alt: str | None = None) -> dict:
        """Set a blog post's cover image.

        The cover is what listing cards and social-media previews show. Unlike
        events, it is uploaded directly rather than picked from the gallery.

        Args:
            identifier: The post's slug, numeric id or UUID.
            image_path: Absolute path to an image file on this machine.
            alt: Alt text for the cover. Defaults to the post title.
        """
        fields = {"featured_image_alt": alt} if alt else {}
        # The cover lives on the post itself, so this PATCHes the blog rather
        # than creating a gallery row.
        result = client.upload(
            f"blogs/{identifier}/", image_path, fields, method="PATCH", field_name="featured_image"
        )
        return updated("blog", result, DETAIL_KEYS)

    @mcp.tool()
    def upload_blog_image(
        identifier: str,
        image_path: str,
        alt: str | None = None,
        caption: str | None = None,
        display_order: int | None = None,
    ) -> dict:
        """Add an in-article photo to a blog post's gallery.

        For the cover image use `set_blog_cover_image` instead.

        Args:
            identifier: The post's slug, numeric id or UUID.
            image_path: Absolute path to an image file on this machine.
            alt: Alt text for accessibility and SEO. Defaults to the post title.
            caption: Optional caption shown under the photo.
            display_order: Lower numbers appear first in the gallery.
        """
        fields = {"alt": alt, "caption": caption, "display_order": display_order}
        return created("blog_image", client.upload(f"blogs/{identifier}/images/", image_path, fields), IMAGE_KEYS)

    @mcp.tool()
    def delete_blog(identifier: str) -> dict:
        """Permanently delete a blog post and its gallery photos.

        This cannot be undone. To hide a post instead, call `update_blog` with
        `is_published=False`.

        Args:
            identifier: The post's slug, numeric id or UUID.
        """
        client.delete(f"blogs/{identifier}/")
        return {"status": "deleted", "type": "blog", "identifier": identifier}
