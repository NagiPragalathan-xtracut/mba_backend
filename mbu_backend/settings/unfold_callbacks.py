"""Callables referenced by the ``UNFOLD`` settings dict."""

from django.conf import settings


def environment_callback(request):
    """
    Render an environment badge in the admin header.

    Returns ``[label, colour]`` where colour is one of Unfold's badge variants
    (``info``, ``warning``, ``danger``, ``success``). Returning ``None`` hides
    the badge, which is what we want on production.
    """
    if settings.DEBUG:
        return ["Development", "warning"]
    return None
