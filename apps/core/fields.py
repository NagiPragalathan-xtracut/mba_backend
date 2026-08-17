"""
Custom model fields.

`SVGImageField` behaves exactly like Django's `ImageField` but additionally
accepts SVG uploads. Django validates images through Pillow, which cannot open
SVG (it is XML, not a raster format), so a plain `ImageField` rejects every
logo/icon the marketing team hands over. This field keeps the Pillow check for
raster formats and falls back to an XML sanity check for SVG.
"""

import logging
import xml.etree.ElementTree as ElementTree

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

logger = logging.getLogger(__name__)

SVG_MIME_TYPES = {"image/svg+xml", "image/svg"}
RASTER_EXTENSIONS = ("png", "jpg", "jpeg", "gif", "webp", "bmp", "avif")
ALLOWED_EXTENSIONS = (*RASTER_EXTENSIONS, "svg")


def looks_like_svg(uploaded_file) -> bool:
    """
    True when ``uploaded_file`` parses as XML whose root element is ``<svg>``.

    Content is checked rather than the file name so a renamed ``.svg`` cannot
    smuggle arbitrary markup past the raster validation path.
    """
    if uploaded_file is None:
        return False

    try:
        uploaded_file.seek(0)
        # `iterparse` stops at the first element, so a huge file is not read
        # into memory just to identify it.
        for _, element in ElementTree.iterparse(uploaded_file, events=("start",)):
            tag = element.tag
            # ElementTree reports namespaced tags as `{http://...}svg`.
            local_name = tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""
            return local_name.lower() == "svg"
    except (ElementTree.ParseError, ValueError, AttributeError, UnicodeDecodeError):
        return False
    finally:
        try:
            uploaded_file.seek(0)
        except (AttributeError, ValueError):  # already closed / not seekable
            logger.debug("Could not rewind uploaded file during SVG detection")

    return False


def validate_upload_size(uploaded_file) -> None:
    """Reject uploads larger than ``settings.MAX_UPLOAD_SIZE_MB``."""
    limit_mb = getattr(settings, "MAX_UPLOAD_SIZE_MB", 10)
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > limit_mb * 1024 * 1024:
        raise ValidationError(
            f"File is too large ({size / 1024 / 1024:.1f} MB). Maximum allowed size is {limit_mb} MB."
        )


class SVGAndImageFormField(forms.ImageField):
    """Form field accepting raster images (validated by Pillow) and SVG."""

    def to_python(self, data):
        try:
            return super().to_python(data)
        except ValidationError:
            # Pillow refused the file. It is still valid if it is a real SVG;
            # anything else re-raises the original, more descriptive error.
            if looks_like_svg(data):
                return forms.FileField.to_python(self, data)
            raise


class SVGImageField(models.ImageField):
    """Model field storing raster images or SVG files."""

    def formfield(self, **kwargs):
        return super().formfield(**{"form_class": SVGAndImageFormField, **kwargs})

    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        # `value` is a FieldFile on unchanged saves and an UploadedFile on new
        # uploads; only the latter carries a size worth checking.
        if hasattr(value, "file") and hasattr(value.file, "size"):
            validate_upload_size(value.file)
        return value
