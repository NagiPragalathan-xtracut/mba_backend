"""Local development settings - convenient, never for public deployment."""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env  # noqa: F401

DEBUG = True

# Any host is fine on a dev machine (covers LAN testing from phones/tablets).
ALLOWED_HOSTS = ["*"]

# Browsable API + a permissive CORS policy so a local frontend can hit the API.
CORS_ALLOW_ALL_ORIGINS = True

# Serve static files straight from disk; no manifest hashing while iterating.
# The media ("default") backend is left exactly as `base` resolved it, so a
# developer can flip USE_S3=True and exercise the real bucket locally.
STORAGES = {
    **globals()["STORAGES"],
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Emails go to the console instead of a real SMTP server.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
