"""
Production settings.

Every value that could leak or differ per deployment comes from the
environment. The module fails loudly at import time when a required secret is
missing - better than booting with an insecure default.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# No fallback: a production boot without an explicit secret key must fail.
SECRET_KEY = env.str("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

# ---------------------------------------------------------------------------
# Transport & cookie security (assumes TLS terminates at the proxy)
# ---------------------------------------------------------------------------

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

# The browsable API is a debugging aid - JSON only in production.
REST_FRAMEWORK = {
    **globals()["REST_FRAMEWORK"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
