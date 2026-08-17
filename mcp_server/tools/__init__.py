"""
MCP tool modules.

Each module exposes a `register(mcp, client)` function that attaches its tools
to the server. Splitting them by domain keeps every file small and makes it
obvious where a new tool belongs.
"""

from mcp_server.tools import blogs, events, faculty, taxonomy

#: Registered in this order, which is also the order Claude sees them in.
#: Taxonomy first: those are the lookups every other tool depends on.
MODULES = (taxonomy, events, blogs, faculty)


def register_all(mcp, client) -> int:
    """Attach every tool module. Returns the number of modules registered."""
    for module in MODULES:
        module.register(mcp, client)
    return len(MODULES)


__all__ = ["register_all", "MODULES", "taxonomy", "events", "blogs", "faculty"]
