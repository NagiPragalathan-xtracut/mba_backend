"""Text helpers.

CKEditor stores HTML, but SEO tags (meta description, OG tags, schema.org)
must contain plain text. These helpers do that conversion in one place so the
rules never drift between apps.
"""

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
# Script/style bodies must go entirely - stripping only the tags would leave
# their source code behind in the description.
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def strip_html(value: str | None) -> str:
    """Return ``value`` with all HTML markup and entities removed."""
    if not value:
        return ""
    text = _SCRIPT_STYLE_RE.sub(" ", str(value))
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return clean_whitespace(text)


def clean_whitespace(value: str | None) -> str:
    """Collapse runs of whitespace into single spaces and trim the ends."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", str(value)).strip()


def summarise(value: str | None, limit: int = 160) -> str:
    """
    Plain-text summary of ``value``, at most ``limit`` characters.

    Truncation happens on a word boundary and appends an ellipsis so meta
    descriptions never end mid-word.
    """
    text = strip_html(value)
    if len(text) <= limit:
        return text

    # Reserve one character for the ellipsis, then back off to a word break.
    clipped = text[: limit - 1]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return f"{clipped.rstrip(',.;:- ')}…"
