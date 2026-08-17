"""
HTTP client for the MBU backend API.

Wraps httpx with the two things every tool needs and none should repeat: token
authentication, and turning HTTP failures into short, actionable messages a
language model can act on (rather than a wall of HTML or a bare status code).
"""

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from mcp_server.config import Settings

logger = logging.getLogger(__name__)

# Images the backend accepts. Checked here too so an obvious mistake fails
# immediately instead of after a full upload.
ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".avif", ".svg"}

CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".avif": "image/avif",
    ".svg": "image/svg+xml",
}


class APIError(RuntimeError):
    """A backend call failed. The message is safe to show to the model."""


class MBUClient:
    """Thin, synchronous wrapper around the MBU REST API."""

    def __init__(self, settings: Settings):
        self.settings = settings

    # ------------------------------------------------------------------
    # Plumbing
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.settings.api_token:
            headers["Authorization"] = f"Token {self.settings.api_token}"
        return headers

    def _url(self, path: str) -> str:
        return f"{self.settings.api_root}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = self._url(path)
        try:
            with httpx.Client(timeout=self.settings.timeout, follow_redirects=True) as client:
                response = client.request(method, url, headers=self._headers(), **kwargs)
        except httpx.ConnectError as exc:
            raise APIError(
                f"Cannot reach the backend at {self.settings.api_base_url}. "
                f"Is the Django server running? ({exc})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise APIError(f"The backend did not respond within {self.settings.timeout}s.") from exc

        return self._handle_response(response, method, url)

    def _handle_response(self, response: httpx.Response, method: str, url: str) -> Any:
        if response.is_success:
            if response.status_code == 204 or not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                return {"raw": response.text[:500]}

        # Turn the failure into something the model can act on.
        detail = self._extract_error(response)

        if response.status_code == 401:
            raise APIError(
                "Authentication failed (401). MBU_API_TOKEN is missing or invalid. "
                "Generate one with: python manage.py create_api_token --username mcp-bot --create-user"
            )
        if response.status_code == 403:
            raise APIError(f"Permission denied (403). The token's user lacks rights for {method} {url}. {detail}")
        if response.status_code == 404:
            raise APIError(f"Not found (404): {url}. Check the slug or id you passed. {detail}")
        if response.status_code == 400:
            raise APIError(f"The backend rejected the data (400): {detail}")

        raise APIError(f"Backend returned {response.status_code} for {method} {url}: {detail}")

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        """Flatten a DRF error body into one readable line."""
        try:
            payload = response.json()
        except ValueError:
            return response.text[:300].replace("\n", " ")

        if isinstance(payload, dict):
            parts = []
            for field, messages in payload.items():
                if isinstance(messages, (list, tuple)):
                    parts.append(f"{field}: {'; '.join(str(m) for m in messages)}")
                else:
                    parts.append(f"{field}: {messages}")
            return " | ".join(parts)
        return str(payload)[:300]

    # ------------------------------------------------------------------
    # Verbs
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=self._clean(params))

    def post(self, path: str, payload: dict) -> Any:
        return self._request("POST", path, json=self._clean(payload))

    def patch(self, path: str, payload: dict) -> Any:
        return self._request("PATCH", path, json=self._clean(payload))

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def upload(
        self,
        path: str,
        image_path: str,
        fields: dict | None = None,
        method: str = "POST",
        field_name: str = "image",
    ) -> Any:
        """
        Send a local image file as multipart/form-data.

        ``image_path`` must be a path on the machine running this MCP server.
        Use ``method="PATCH"`` to attach the file to an existing object (a blog
        cover, a faculty photo) rather than creating a new row, and
        ``field_name`` to match the form field the endpoint expects - gallery
        endpoints use ``image``, a blog cover uses ``featured_image``.
        """
        file_path = Path(image_path).expanduser()

        if not file_path.is_file():
            raise APIError(
                f"No file at '{file_path}'. Pass an absolute path to an image on this machine."
            )

        suffix = file_path.suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise APIError(
                f"'{suffix or file_path.name}' is not a supported image type. "
                f"Use one of: {', '.join(sorted(ALLOWED_IMAGE_SUFFIXES))}"
            )

        with file_path.open("rb") as handle:
            files = {field_name: (file_path.name, handle, CONTENT_TYPES.get(suffix, "application/octet-stream"))}
            data = {key: str(value) for key, value in self._clean(fields).items()}
            return self._request(method, path, files=files, data=data)

    # ------------------------------------------------------------------

    @staticmethod
    def _clean(payload: dict | None) -> dict:
        """Drop ``None`` values so optional tool arguments mean "leave unset"."""
        if not payload:
            return {}
        return {key: value for key, value in payload.items() if value is not None}

    # ------------------------------------------------------------------

    def health(self) -> dict:
        """Check connectivity and whether the token authenticates."""
        result = self.get("health/")
        parsed = urlparse(self.settings.api_base_url)
        return {
            "backend": f"{parsed.scheme}://{parsed.netloc}",
            "token_configured": self.settings.is_configured,
            **(result if isinstance(result, dict) else {}),
        }
