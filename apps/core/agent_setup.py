"""
The setup prompt an admin hands to an AI agent.

Written for any agent that can run shell commands - Claude Code, Cursor,
Codex, VS Code's agent mode and the like. Pasted into one, it installs only the
MCP server (`mcp_server/` needs `mcp` and `httpx`, not Django), registers it
with whichever MCP client the agent runs in, and checks the token works.

Plain Python rather than a template so the exact text is easy to test.
"""

import json
from dataclasses import dataclass

SERVER_NAME = "mbu-backend"

# The MCP server's only dependencies. These must match requirements.txt - a
# test fails if the two drift apart.
MCP_REQUIREMENTS = ("mcp==1.27.0", "httpx==0.28.1")

INSTALL_DIR_POSIX = "~/.mcp-servers/mbu-backend"
INSTALL_DIR_WINDOWS = "%USERPROFILE%\\.mcp-servers\\mbu-backend"


@dataclass(frozen=True)
class AgentSetup:
    """Everything an agent needs to connect, plus the text that tells it how."""

    site_name: str
    api_base_url: str
    token: str
    username: str
    repo_url: str
    repo_branch: str = "main"

    @property
    def health_url(self) -> str:
        return f"{self.api_base_url}/api/v1/health/"

    @property
    def archive_url(self) -> str:
        """ZIP download for agents without git (GitHub's URL layout)."""
        base = self.repo_url.removesuffix(".git")
        return f"{base}/archive/refs/heads/{self.repo_branch}.zip"

    def env(self, install_dir: str = "INSTALL_DIR") -> dict[str, str]:
        return {
            "PYTHONPATH": install_dir,
            "MBU_API_BASE_URL": self.api_base_url,
            "MBU_API_TOKEN": self.token,
            "MBU_API_TIMEOUT": "60",
        }

    def client_config(self, python: str = "PYTHON", install_dir: str = "INSTALL_DIR") -> str:
        """The server entry in the `mcpServers` JSON shape most clients use."""
        config = {
            "mcpServers": {
                SERVER_NAME: {
                    "command": python,
                    "args": ["-m", "mcp_server"],
                    "env": self.env(install_dir),
                }
            }
        }
        return json.dumps(config, indent=2)

    def env_file(self) -> str:
        """`.env` lines for someone running the server from their own checkout."""
        return "\n".join(f"{key}={value}" for key, value in self.env().items() if key != "PYTHONPATH")

    def prompt(self) -> str:
        reqs = " ".join(f'"{requirement}"' for requirement in MCP_REQUIREMENTS)
        base = self.api_base_url
        token = self.token
        name = SERVER_NAME

        return f"""\
Install and connect the "{name}" MCP server on this computer, so that you - and any future session - can manage content on the {self.site_name} website through it. Do every step yourself instead of asking me to run commands, and only stop to ask if something fails in a way you cannot fix.

CONNECTION DETAILS
- API base URL: {base}
- API token: {token}
  This token can create, edit and delete content on the live website. Treat it like a password: never commit it to a repository, never post it anywhere public, and do not repeat it back to me in full.
- Server code: {self.repo_url} (public, branch "{self.repo_branch}"). The server is the mcp_server/ package in that repository. It needs only Python and two packages - do NOT install the repository's requirements.txt or set up Django.

STEPS
1. Install folder: {INSTALL_DIR_POSIX} (on Windows: {INSTALL_DIR_WINDOWS}). Below it is called INSTALL_DIR - always expand it to an absolute path.
   - If INSTALL_DIR is already a git checkout, update it: git -C INSTALL_DIR pull --ff-only
   - Otherwise: git clone --depth 1 --branch {self.repo_branch} {self.repo_url} INSTALL_DIR
   - Without git: download {self.archive_url} and extract it so that INSTALL_DIR/mcp_server/ exists.

2. Create a virtual environment at INSTALL_DIR/.venv with Python 3.10-3.13 and install exactly: {reqs}
   - With uv: uv venv --python 3.12 INSTALL_DIR/.venv, then uv pip install --python INSTALL_DIR/.venv {reqs}
   - Without uv: python -m venv INSTALL_DIR/.venv, then install with that venv's pip.
   PYTHON below means that venv's interpreter as an absolute path: INSTALL_DIR/.venv/bin/python, or INSTALL_DIR\\.venv\\Scripts\\python.exe on Windows.

3. Check the token before changing any configuration (in Windows PowerShell, call curl.exe rather than curl):
   curl -s -H "Authorization: Token {token}" {self.health_url}
   Expect "status": "healthy", "authenticated": true and "user": "{self.username}". If "authenticated" is false, stop and tell me the token was rejected.

4. Smoke-test the server. With PYTHONPATH=INSTALL_DIR and the MBU_* variables from step 5 set in the environment, run:
   PYTHON -c "import asyncio, mcp_server.server as s; print(len(asyncio.run(s.build_server().list_tools())), 'tools')"
   It must print a tool count, not an error.

5. Register a stdio MCP server named "{name}" with the MCP client you are running in, for my user account (every project), not only the current folder:
   - command: PYTHON
   - args: -m mcp_server
   - environment: PYTHONPATH=INSTALL_DIR, MBU_API_BASE_URL={base}, MBU_API_TOKEN={token}, MBU_API_TIMEOUT=60
   Where it goes:
   - Claude Code: claude mcp add --scope user --env PYTHONPATH=INSTALL_DIR --env MBU_API_BASE_URL={base} --env MBU_API_TOKEN={token} --env MBU_API_TIMEOUT=60 {name} -- PYTHON -m mcp_server
     (if "{name}" is already registered, first run: claude mcp remove --scope user {name})
   - Claude Desktop: the "mcpServers" object in claude_desktop_config.json (%APPDATA%\\Claude\\ on Windows, ~/Library/Application Support/Claude/ on macOS).
   - Cursor: "mcpServers" in ~/.cursor/mcp.json.
   - VS Code agent mode: "servers" in the user-level mcp.json, with "type": "stdio".
   - Codex CLI: a [mcp_servers.{name}] table in ~/.codex/config.toml with command, args and env.
   - Any other client: its own MCP configuration, with the same command, args and environment.
   When editing a config file, merge into it and keep every server already there. The entry in the common JSON shape (replace PYTHON and INSTALL_DIR with absolute paths):
{self.client_config()}

6. Report back in a few lines: the install folder, the config file or command you used, and the result of step 3. Tell me whether I need to restart or reload the client for the new tools to appear. Once they appear, the "check_backend" tool should report "authenticated": true and "user": "{self.username}".
"""
