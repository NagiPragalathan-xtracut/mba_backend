"""
MCP server exposing the MBU backend to Claude.

Claude talks to this process over stdio; this process talks to the Django REST
API over HTTP with a token. That indirection is deliberate - the same server
works against a local dev backend or a deployed one, and every write goes
through the same validation the admin uses.

Run it with:  python -m mcp_server
"""

__version__ = "1.0.0"
