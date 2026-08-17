"""Local development settings - convenient, never for public deployment."""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env  # noqa: F401

DEBUG = True

# Any host is fine on a dev machine (covers LAN testing from phones/tablets).
ALLOWED_HOSTS = ["*"]

# Browsable API + a permissive CORS policy so a local frontend can hit the API.
CORS_ALLOW_ALL_ORIGINS = True

# Serve static files straight from disk; no manifest hashing while iterating.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Emails go to the console instead of a real SMTP server.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
