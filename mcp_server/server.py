"""
The MCP server itself.

Builds a FastMCP instance, wires in the API client and registers every tool
module. The `instructions` string below is what Claude reads before choosing a
tool, so it carries the workflow rules that are easy to get wrong: look up
slugs before using them, create content before uploading its images.
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from mcp_server.client import MBUClient
from mcp_server.config import load_settings
from mcp_server.tools import register_all

# Log to stderr: stdout is the MCP transport and must carry only protocol data.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="[%(levelname)s] mcp_server: %(message)s",
)
logger = logging.getLogger(__name__)

INSTRUCTIONS = """\
Content management for the Mohan Babu University website. Use these tools to
create and update events, blog posts and faculty profiles.

How the content is organised:

* **Events** are announcements and achievements. Each has exactly one category
  (usually "upcoming" or "achievements") and any number of departments. An
  event's highlight image is chosen from the photos uploaded to its gallery.
* **Blogs** are articles. Each has any number of categories and departments,
  plus one cover image uploaded directly.
* **Faculty** are staff profiles. Each has one designation and any number of
  departments. A profile's long-form content is built from repeatable
  "heading + body" sections - add one per topic (Biography, Publications,
  Awards, ...) rather than cramming everything into one block.

Rules that matter:

1. Departments, categories and designations are referenced **by slug**. Call
   the matching `list_*` tool first; passing a slug that does not exist is
   rejected. Only create a new one when nothing suitable already exists.
2. Create the event, blog or faculty member **before** uploading its images -
   uploads attach to something that already exists.
3. Image paths must be absolute paths to files on this machine.
4. Do not write SEO fields. Meta titles, descriptions, Open Graph tags,
   Twitter cards and schema.org JSON-LD are generated automatically and stay
   in sync as content changes.
5. Prefer unpublishing (`is_published=False`) over deleting. Deletes are
   permanent and take gallery images with them.
6. If a tool fails, run `check_backend` to tell a stopped server apart from a
   bad token apart from invalid data.
"""


def build_server() -> FastMCP:
    """Construct the MCP server with every tool registered."""
    settings = load_settings()
    client = MBUClient(settings)

    mcp = FastMCP(name="mbu-backend", instructions=INSTRUCTIONS)
    module_count = register_all(mcp, client)

    logger.info("Backend: %s", settings.api_base_url)
    logger.info("Registered %d tool modules", module_count)

    if not settings.is_configured:
        # Not fatal: read-only tools still work, and saying so up front beats
        # a confusing 401 on the first write.
        logger.warning(
            "MBU_API_TOKEN is not set - read tools will work but every write will fail with 401. "
            "Generate a token with: python manage.py create_api_token --username mcp-bot --create-user"
        )

    return mcp


def main() -> None:
    """Entry point: serve over stdio."""
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
