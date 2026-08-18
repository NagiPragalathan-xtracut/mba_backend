"""Date helpers."""

from datetime import date, datetime, time


def iso_date(value) -> str:
    """
    Render a date field as an ISO-8601 string.

    Django accepts a string for a ``DateField`` and only converts it on the
    next read from the database, so a freshly assigned instance can hold either
    a ``date`` or a ``str``. Schema generation runs before that conversion, so
    it has to handle both.
    """
    if not value:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _coerce_date(value):
    """Return ``value`` as a ``date``, or ``None`` when it is not one.

    Same reason as ``iso_date``: a freshly assigned ``DateField`` can still be
    holding the string the caller passed in.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def short_date(value) -> str:
    """Day and abbreviated month, e.g. ``"18 Dec"`` - the listing date badge."""
    parsed = _coerce_date(value)
    return f"{parsed.day:02d} {parsed.strftime('%b')}" if parsed else ""


def long_date(value) -> str:
    """Day, month and year, e.g. ``"15 Jan 2025"`` - the blog card date."""
    parsed = _coerce_date(value)
    return f"{parsed.day:02d} {parsed.strftime('%b %Y')}" if parsed else ""


def dotted_date(value) -> str:
    """Dotted numeric date, e.g. ``"18.12.2024"`` - the detail page's date line."""
    parsed = _coerce_date(value)
    return parsed.strftime("%d.%m.%Y") if parsed else ""


def format_clock_time(value) -> str:
    """
    12-hour clock without a leading zero, e.g. ``"10:00 AM"``.

    ``%-I`` is not portable (it fails on Windows), so the hour is derived
    arithmetically instead of through ``strftime``.
    """
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = time.fromisoformat(value)
        except ValueError:
            return value
    hour = value.hour % 12 or 12
    meridiem = "AM" if value.hour < 12 else "PM"
    return f"{hour}:{value.minute:02d} {meridiem}"
