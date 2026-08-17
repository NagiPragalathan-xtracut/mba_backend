"""Slug generation shared by every sluggable model."""

from django.utils.text import slugify


def unique_slugify(instance, source_value: str, slug_field_name: str = "slug", max_length: int = 255) -> str:
    """
    Build a slug for ``instance`` that is unique across its model.

    ``source_value`` is slugified and, when that value is already taken by a
    *different* row, a numeric suffix is appended (``my-event``, ``my-event-1``,
    ...). The instance itself is excluded from the check so re-saving an object
    never bumps its own slug.
    """
    base_slug = slugify(source_value) or "item"
    base_slug = base_slug[:max_length].rstrip("-")

    model = instance.__class__
    queryset = model._default_manager.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    slug = base_slug
    counter = 1
    while queryset.filter(**{slug_field_name: slug}).exists():
        suffix = f"-{counter}"
        # Keep the result within the column limit even after the suffix.
        slug = f"{base_slug[: max_length - len(suffix)].rstrip('-')}{suffix}"
        counter += 1

    return slug
