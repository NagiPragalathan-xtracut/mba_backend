"""
Taxonomy tools: departments, event categories, blog categories, designations.

These are the lookup tables everything else references by slug, so in practice
Claude calls `list_departments` (or a sibling) before creating content, to
learn which slugs exist.
"""

from mcp_server.client import MBUClient
from mcp_server.tools._common import compact, created, listing

TAXONOMY_KEYS = ("id", "name", "slug", "short_name", "description", "display_order", "is_active")


def register(mcp, client: MBUClient) -> None:
    """Attach the taxonomy tools to the MCP server."""

    # ------------------------------------------------------------------
    # Departments
    # ------------------------------------------------------------------

    @mcp.tool()
    def list_departments(search: str | None = None) -> dict:
        """List academic departments with the slugs used to tag content.

        Departments are shared by events, blogs and faculty. Call this first
        when you need to know which department slugs are valid - passing a slug
        that does not exist will be rejected.

        Args:
            search: Optional text to match against name, short name or description.
        """
        return listing(client.get("departments/", {"search": search, "page_size": 100}), TAXONOMY_KEYS)

    @mcp.tool()
    def create_department(
        name: str,
        short_name: str | None = None,
        description: str | None = None,
        display_order: int | None = None,
    ) -> dict:
        """Create an academic department.

        Only create one after checking `list_departments` - departments are
        shared across the whole site and duplicates are hard to untangle later.

        Args:
            name: Full department name, e.g. "Computer Science & Engineering".
            short_name: Abbreviation shown in compact UI, e.g. "CSE".
            description: Optional description.
            display_order: Lower numbers appear first on the website.
        """
        payload = {
            "name": name,
            "short_name": short_name,
            "description": description,
            "display_order": display_order,
        }
        return created("department", client.post("departments/", payload), TAXONOMY_KEYS)

    # ------------------------------------------------------------------
    # Event categories
    # ------------------------------------------------------------------

    @mcp.tool()
    def list_event_categories() -> dict:
        """List event categories. The site ships with "Upcoming" and "Achievements".

        Every event needs exactly one category, referenced by slug.
        """
        return listing(client.get("event-categories/", {"page_size": 100}), TAXONOMY_KEYS)

    @mcp.tool()
    def create_event_category(name: str, description: str | None = None, display_order: int | None = None) -> dict:
        """Create a new event category, e.g. "Workshops" or "Convocation".

        Args:
            name: Category name.
            description: Optional description.
            display_order: Lower numbers appear first.
        """
        payload = {"name": name, "description": description, "display_order": display_order}
        return created("event_category", client.post("event-categories/", payload), TAXONOMY_KEYS)

    # ------------------------------------------------------------------
    # Blog categories
    # ------------------------------------------------------------------

    @mcp.tool()
    def list_blog_categories() -> dict:
        """List blog categories, e.g. "Research", "Campus Life", "Placements".

        A blog post can belong to several categories, referenced by slug.
        """
        return listing(client.get("blog-categories/", {"page_size": 100}), TAXONOMY_KEYS)

    @mcp.tool()
    def create_blog_category(name: str, description: str | None = None, display_order: int | None = None) -> dict:
        """Create a new blog category.

        Args:
            name: Category name.
            description: Optional description.
            display_order: Lower numbers appear first.
        """
        payload = {"name": name, "description": description, "display_order": display_order}
        return created("blog_category", client.post("blog-categories/", payload), TAXONOMY_KEYS)

    # ------------------------------------------------------------------
    # Designations
    # ------------------------------------------------------------------

    @mcp.tool()
    def list_designations() -> dict:
        """List faculty designations (job titles) such as "Professor".

        Every faculty profile needs exactly one designation, referenced by slug.
        """
        return listing(client.get("designations/", {"page_size": 100}), TAXONOMY_KEYS)

    @mcp.tool()
    def create_designation(name: str, description: str | None = None, display_order: int | None = None) -> dict:
        """Create a faculty designation, e.g. "Adjunct Professor".

        Args:
            name: Job title.
            description: Optional description.
            display_order: Lower numbers appear first - useful for seniority.
        """
        payload = {"name": name, "description": description, "display_order": display_order}
        return created("designation", client.post("designations/", payload), TAXONOMY_KEYS)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @mcp.tool()
    def check_backend() -> dict:
        """Check that the MBU backend is reachable and the API token works.

        Run this first if any other tool fails - it distinguishes "server is
        down" from "token is wrong" from "the data was invalid".
        """
        return compact(
            client.health(),
            ("backend", "status", "database", "token_configured", "authenticated", "user"),
        )
