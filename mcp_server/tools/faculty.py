"""Faculty tools: profiles, their repeatable sections and their images."""

from mcp_server.client import MBUClient
from mcp_server.tools._common import as_paragraphs, compact, created, listing, split_csv, updated

LIST_KEYS = (
    "id", "name", "slug", "designation_name", "departments",
    "qualification", "mail_id", "is_published", "display_order",
)
DETAIL_KEYS = (
    "id", "name", "slug", "designation", "departments", "qualification",
    "mail_id", "phone_number", "profile_link", "image_url",
    "is_published", "is_featured", "display_order", "meta_title", "meta_description", "keywords",
)
SECTION_KEYS = ("id", "heading", "display_order", "is_visible")


def register(mcp, client: MBUClient) -> None:
    """Attach the faculty tools to the MCP server."""

    @mcp.tool()
    def list_faculty(
        department: str | None = None,
        designation: str | None = None,
        search: str | None = None,
        page: int | None = None,
    ) -> dict:
        """List faculty profiles.

        Args:
            department: Department slug, e.g. "computer-science-engineering".
            designation: Designation slug, e.g. "professor".
            search: Free-text search across name, qualification, email and section text.
            page: Page number (20 per page).
        """
        params = {"department": department, "designation": designation, "search": search, "page": page}
        return listing(client.get("faculty/", params), LIST_KEYS)

    @mcp.tool()
    def get_faculty(identifier: str) -> dict:
        """Fetch one faculty profile in full, including its sections.

        Args:
            identifier: The profile's slug, numeric id or UUID.
        """
        result = client.get(f"faculty/{identifier}/")
        detail = compact(result, DETAIL_KEYS)
        detail["sections"] = [compact(section, SECTION_KEYS) for section in result.get("sections", [])]
        return detail

    @mcp.tool()
    def create_faculty(
        name: str,
        designation: str,
        departments: str | None = None,
        qualification: str | None = None,
        mail_id: str | None = None,
        phone_number: str | None = None,
        profile_link: str | None = None,
        display_order: int | None = None,
        is_published: bool = True,
        is_featured: bool = False,
    ) -> dict:
        """Create a faculty profile.

        A profile's long-form content is not a fixed set of fields: add as many
        "heading + body" blocks as the person needs (Biography, Publications,
        Awards, Patents, ...) with `add_faculty_section` after creating them.

        SEO metadata is generated automatically - do not supply it.

        Args:
            name: Full name as it should appear publicly, e.g. "Dr. Anitha Rao".
            designation: Designation slug from `list_designations`, e.g. "professor".
            departments: Comma-separated department slugs. A person may belong
                to more than one, e.g. "ece, mechanical-engineering".
            qualification: Degrees and certifications, e.g. "Ph.D., M.Tech, B.Tech".
            mail_id: Optional public email address.
            phone_number: Optional public phone number.
            profile_link: Optional personal site, Google Scholar or ORCID URL.
            display_order: Lower numbers appear first in the directory.
            is_published: Whether the profile is visible on the public website.
            is_featured: Whether to highlight it in the directory.
        """
        payload = {
            "name": name,
            "designation": designation,
            "departments": split_csv(departments),
            "qualification": qualification,
            "mail_id": mail_id,
            "phone_number": phone_number,
            "profile_link": profile_link,
            "display_order": display_order,
            "is_published": is_published,
            "is_featured": is_featured,
        }
        return created("faculty", client.post("faculty/", payload), DETAIL_KEYS)

    @mcp.tool()
    def update_faculty(
        identifier: str,
        name: str | None = None,
        designation: str | None = None,
        departments: str | None = None,
        qualification: str | None = None,
        mail_id: str | None = None,
        phone_number: str | None = None,
        profile_link: str | None = None,
        display_order: int | None = None,
        is_published: bool | None = None,
        is_featured: bool | None = None,
    ) -> dict:
        """Update a faculty profile. Only the arguments you pass are changed.

        To change the profile's sections use `add_faculty_section`,
        `update_faculty_section` or `delete_faculty_section`.

        Args:
            identifier: The profile's slug, numeric id or UUID.
            name: New full name.
            designation: New designation slug.
            departments: Comma-separated department slugs. Replaces the whole set.
            qualification: New qualifications string.
            mail_id: New public email address.
            phone_number: New public phone number.
            profile_link: New external profile URL.
            display_order: New ordering weight.
            is_published: Publish or unpublish.
            is_featured: Feature or unfeature.
        """
        payload = {
            "name": name,
            "designation": designation,
            "departments": split_csv(departments),
            "qualification": qualification,
            "mail_id": mail_id,
            "phone_number": phone_number,
            "profile_link": profile_link,
            "display_order": display_order,
            "is_published": is_published,
            "is_featured": is_featured,
        }
        return updated("faculty", client.patch(f"faculty/{identifier}/", payload), DETAIL_KEYS)

    # ------------------------------------------------------------------
    # Profile sections - the repeatable "heading + rich text" blocks
    # ------------------------------------------------------------------

    @mcp.tool()
    def add_faculty_section(
        identifier: str,
        heading: str,
        content: str,
        display_order: int | None = None,
    ) -> dict:
        """Add a titled content block to a faculty profile.

        This is how a profile gets its Biography, Publications, Awards,
        Workshops, Projects and so on - add one block per topic, in any order.
        Headings must be unique within a profile.

        Args:
            identifier: The profile's slug, numeric id or UUID.
            heading: Section title, e.g. "Publications".
            content: Section body. Plain text is converted to HTML paragraphs;
                HTML (including lists) is stored as given.
            display_order: Lower numbers appear first on the profile page.
        """
        payload = {"heading": heading, "content": as_paragraphs(content), "display_order": display_order}
        return created("faculty_section", client.post(f"faculty/{identifier}/sections/", payload), SECTION_KEYS)

    @mcp.tool()
    def update_faculty_section(
        section_id: int,
        heading: str | None = None,
        content: str | None = None,
        display_order: int | None = None,
        is_visible: bool | None = None,
    ) -> dict:
        """Update one profile section. Use `get_faculty` to find section ids.

        Args:
            section_id: Numeric id of the section.
            heading: New section title.
            content: New body (plain text or HTML).
            display_order: New ordering weight.
            is_visible: Hide the section without deleting it.
        """
        payload = {
            "heading": heading,
            "content": as_paragraphs(content),
            "display_order": display_order,
            "is_visible": is_visible,
        }
        return updated("faculty_section", client.patch(f"faculty-sections/{section_id}/", payload), SECTION_KEYS)

    @mcp.tool()
    def delete_faculty_section(section_id: int) -> dict:
        """Permanently delete one profile section.

        To hide it instead, call `update_faculty_section` with `is_visible=False`.

        Args:
            section_id: Numeric id of the section.
        """
        client.delete(f"faculty-sections/{section_id}/")
        return {"status": "deleted", "type": "faculty_section", "id": section_id}

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    @mcp.tool()
    def set_faculty_photo(identifier: str, image_path: str, alt: str | None = None) -> dict:
        """Set a faculty member's profile photo.

        Args:
            identifier: The profile's slug, numeric id or UUID.
            image_path: Absolute path to an image file on this machine.
                Portrait orientation works best.
            alt: Alt text for the photo. Defaults to the person's name.
        """
        fields = {"image_alt": alt} if alt else {}
        result = client.upload(f"faculty/{identifier}/", image_path, fields, method="PATCH")
        return updated("faculty", result, DETAIL_KEYS)

    @mcp.tool()
    def upload_faculty_banner(
        identifier: str,
        image_path: str,
        alt: str | None = None,
        display_order: int | None = None,
    ) -> dict:
        """Add a wide banner image to a faculty profile page.

        Banners are the page header strip - the portrait photo is set with
        `set_faculty_photo` instead.

        Args:
            identifier: The profile's slug, numeric id or UUID.
            image_path: Absolute path to an image file on this machine.
            alt: Alt text for the banner. Defaults to the person's name.
            display_order: Lower numbers appear first.
        """
        fields = {"alt": alt, "display_order": display_order}
        result = client.upload(f"faculty/{identifier}/banners/", image_path, fields)
        return created("faculty_banner", result, ("id", "alt", "display_order", "image_url"))

    @mcp.tool()
    def delete_faculty(identifier: str) -> dict:
        """Permanently delete a faculty profile, its sections and its images.

        This cannot be undone. To hide a profile instead, call
        `update_faculty` with `is_published=False`.

        Args:
            identifier: The profile's slug, numeric id or UUID.
        """
        client.delete(f"faculty/{identifier}/")
        return {"status": "deleted", "type": "faculty", "identifier": identifier}
