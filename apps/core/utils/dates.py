"""Date helpers."""

from datetime import date, datetime


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
