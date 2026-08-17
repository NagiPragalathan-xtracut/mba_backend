"""Configuration for the MCP server, read from the environment / `.env`."""

import os
from dataclasses import dataclass
from pathlib import Path

# Project root: mcp_server/config.py -> mcp_server -> <root>
BASE_DIR = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    """
    Minimal `.env` loader.

    The MCP server runs as a standalone process without Django loaded, so it
    cannot reuse django-environ. Existing environment variables always win -
    an MCP client passing `env` in its config should override the file.
    """
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    """Everything the MCP server needs to reach the backend."""

    api_base_url: str
    api_token: str
    timeout: float

    @property
    def api_root(self) -> str:
        return f"{self.api_base_url}/api/v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token)


def load_settings() -> Settings:
    """Build settings from the environment, loading `.env` first."""
    _load_dotenv(BASE_DIR / ".env")

    return Settings(
        api_base_url=os.environ.get("MBU_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        api_token=os.environ.get("MBU_API_TOKEN", "").strip(),
        timeout=float(os.environ.get("MBU_API_TIMEOUT", "60")),
    )
