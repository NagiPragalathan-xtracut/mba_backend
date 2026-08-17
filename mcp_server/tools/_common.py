"""
Shared helpers for the MCP tool modules.

Tool results go straight into a language model's context, so they are trimmed
to what is useful: identifiers to act on next, plus the handful of fields a
human would want confirmed. Full rich-text bodies are never echoed back.
"""

from typing import Any

# How much of a paginated list to describe before summarising the rest.
MAX_LISTED = 50


def compact(payload: dict, keys: tuple[str, ...]) -> dict:
    """Keep only ``keys`` that are actually present in ``payload``."""
    return {key: payload[key] for key in keys if key in payload}


def listing(result: Any, keys: tuple[str, ...]) -> dict:
    """
    Normalise a paginated DRF list response into a compact summary.

    Returns the total count alongside trimmed rows so the model can decide
    whether to page further instead of being handed hundreds of full objects.
    """
    if not isinstance(result, dict):
        return {"count": 0, "results": []}

    rows = result.get("results", [])
    return {
        "count": result.get("count", len(rows)),
        "total_pages": result.get("total_pages", 1),
        "current_page": result.get("current_page", 1),
        "has_more": bool(result.get("next")),
        "results": [compact(row, keys) for row in rows[:MAX_LISTED]],
    }


def created(kind: str, payload: dict, keys: tuple[str, ...]) -> dict:
    """Standard confirmation for a successful write."""
    return {
        "status": "created",
        "type": kind,
        **compact(payload, keys),
    }


def updated(kind: str, payload: dict, keys: tuple[str, ...]) -> dict:
    """Standard confirmation for a successful update."""
    return {
        "status": "updated",
        "type": kind,
        **compact(payload, keys),
    }


def split_csv(value: str | None) -> list[str] | None:
    """
    Turn ``"cse, ece"`` into ``["cse", "ece"]``.

    Tool arguments are kept as comma-separated strings rather than arrays
    because that is what models produce most reliably, and it reads naturally
    in a prompt ("departments: cse, ece").
    """
    if value is None:
        return None
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


def as_paragraphs(text: str | None) -> str | None:
    """
    Accept plain text where the backend expects HTML.

    Content fields are CKEditor rich text. If a caller passes plain prose, wrap
    each blank-line-separated block in a ``<p>`` so the stored value is valid
    HTML instead of one unformatted blob. Text that already contains markup is
    passed through untouched.
    """
    if not text:
        return text
    if "<" in text and ">" in text:
        return text

    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    return "".join(f"<p>{block}</p>" for block in blocks) or text
