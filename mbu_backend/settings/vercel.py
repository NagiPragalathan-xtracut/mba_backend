"""
Vercel (serverless) settings.

Vercel runs the app as a short-lived function rather than a long-running
process, which changes four things compared with `production.py`:

* **The filesystem is read-only** apart from `/tmp`. Uploads therefore *must*
  go to S3 - `USE_S3=True` is a hard requirement here, not an option, and the
  module refuses to start without it rather than failing later on the first
  upload with a confusing permission error.
* **Static files are collected at build time** into `staticfiles/` and served
  by Vercel's CDN. The function itself never serves them, so the hashed
  manifest backend is dropped: it would demand a `staticfiles.json` that is not
  bundled with the function and every `{% static %}` tag would raise.
* **The hostname is assigned by the platform.** Preview deployments get a fresh
  `*.vercel.app` subdomain on every push, so that suffix is trusted in addition
  to whatever real domain is configured.
* **Database connections cannot be pooled.** Each invocation is isolated, so a
  reused connection is never actually reused - it just sits open on the server
  until it times out. Concurrent traffic would exhaust MySQL's connection
  limit, so connections are closed at the end of every request.
"""

from django.core.exceptions import ImproperlyConfigured

from .production import *  # noqa: F401,F403
from .production import BASE_DIR, DATABASES, env

# ---------------------------------------------------------------------------
# Media - S3 is mandatory on a read-only filesystem
# ---------------------------------------------------------------------------

if not globals().get("USE_S3"):
    raise ImproperlyConfigured(
        "USE_S3 must be True on Vercel: the filesystem is read-only, so uploaded "
        "media cannot be written to disk. Set USE_S3 and the AWS_* variables in "
        "the Vercel project's environment settings."
    )

# ---------------------------------------------------------------------------
# Hosts - the platform assigns *.vercel.app, custom domains come from the env
# ---------------------------------------------------------------------------

ALLOWED_HOSTS = [*env.list("DJANGO_ALLOWED_HOSTS", default=[]), ".vercel.app"]
CSRF_TRUSTED_ORIGINS = [
    *env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[]),
    "https://*.vercel.app",
]

# Vercel already redirects HTTP to HTTPS at the edge. Doing it again in Django
# risks a redirect loop when the proxy header is missing on an internal request.
SECURE_SSL_REDIRECT = False

# ---------------------------------------------------------------------------
# Static files - collected during the build, served by the CDN
# ---------------------------------------------------------------------------

# Vercel serves the build output directory's *contents* at the site root, so a
# file collected to `<distDir>/x.css` is published at `/x.css`. Collecting into
# a nested `static/` folder is therefore what makes `/static/x.css` - the URL
# Django writes into every template - actually resolve. `distDir` in
# vercel.json must stay in sync with the directory named here.
STATIC_ROOT = BASE_DIR / "staticfiles_build" / "static"

STORAGES = {
    **globals()["STORAGES"],
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# ---------------------------------------------------------------------------
# Database - no connection reuse between invocations
# ---------------------------------------------------------------------------

DATABASES["default"]["CONN_MAX_AGE"] = 0
