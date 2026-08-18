"""
Base Django settings shared by every environment.

Environment-specific modules (`development.py`, `production.py`) import
everything from here and override only what differs. Nothing secret lives in
this file - all credentials are read from the environment / `.env`.
"""

from pathlib import Path

import environ
from django.urls import reverse_lazy

from .storage import build_media_storage

# ---------------------------------------------------------------------------
# Paths & environment
# ---------------------------------------------------------------------------

# mbu_backend/settings/base.py -> mbu_backend/settings -> mbu_backend -> <root>
BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    CORS_ALLOW_ALL_ORIGINS=(bool, False),
    SITE_BASE_URL=(str, "http://localhost:8000"),
    SITE_NAME=(str, "Mohan Babu University"),
    DJANGO_TIME_ZONE=(str, "Asia/Kolkata"),
    DJANGO_LANGUAGE_CODE=(str, "en-us"),
    MEDIA_ROOT=(str, "media"),
    STATIC_ROOT=(str, "staticfiles"),
)

# Read `.env` from the project root when present. Missing file is not an error:
# in production the values usually come from real environment variables.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="django-insecure-dev-only-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Public identity of the site - used when building canonical / OG URLs.
SITE_BASE_URL = env.str("SITE_BASE_URL").rstrip("/")
SITE_NAME = env.str("SITE_NAME")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

# `unfold` and its contrib packages MUST come before `django.contrib.admin`
# so their templates take precedence over the stock admin templates.
UNFOLD_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "ckeditor",
    "ckeditor_uploader",
]

LOCAL_APPS = [
    "apps.core",
    "apps.events",
    "apps.blogs",
    "apps.faculty",
]

INSTALLED_APPS = UNFOLD_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mbu_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mbu_backend.wsgi.application"
ASGI_APPLICATION = "mbu_backend.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# `DATABASE_URL` wins when provided (Postgres/MySQL in staging & production);
# otherwise fall back to a local SQLite file so a fresh clone runs immediately.
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# MySQL needs three things a connection URL cannot express:
#
# * **utf8mb4** - MySQL's "utf8" is a three-byte subset that cannot store emoji
#   or many CJK characters, so editors pasting them into CKEditor would hit a
#   database error rather than a validation one.
# * **TLS** - the managed database requires an encrypted connection.
# * **STRICT_TRANS_TABLES** - without it MySQL silently truncates over-long
#   values instead of raising, which would quietly corrupt content.
if DATABASES["default"]["ENGINE"].endswith("mysql"):
    options = DATABASES["default"].setdefault("OPTIONS", {})
    options.setdefault("charset", "utf8mb4")
    options.setdefault("init_command", "SET sql_mode='STRICT_TRANS_TABLES'")

    # `ssl_mode`, NOT an `ssl` dict. mysqlclient ignores an empty `ssl={}`, and
    # an unencrypted connection makes MySQL 8 reject `caching_sha2_password`
    # logins - which it reports as "Access denied", not as a TLS failure. That
    # misdiagnosis costs an hour, so the mode is set explicitly.
    #
    # REQUIRED encrypts without verifying the server certificate, which is what
    # a managed host with a self-signed certificate needs. Point
    # DATABASE_SSL_CA at a CA bundle and raise the mode to VERIFY_CA (or
    # VERIFY_IDENTITY) to authenticate the server as well.
    ssl_mode = env.str("DATABASE_SSL_MODE", default="REQUIRED").upper()
    if ssl_mode != "DISABLED":
        options.setdefault("ssl_mode", ssl_mode)
        ssl_ca = env.str("DATABASE_SSL_CA", default="")
        if ssl_ca:
            options.setdefault("ssl", {"ca": ssl_ca})

    # Reuse connections between requests; MySQL handshakes are expensive over a
    # network link. `CONN_HEALTH_CHECKS` discards ones the server has dropped.
    DATABASES["default"].setdefault("CONN_MAX_AGE", env.int("DATABASE_CONN_MAX_AGE", default=60))
    DATABASES["default"].setdefault("CONN_HEALTH_CHECKS", True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# The admin is the only login surface here, so point Django's auth redirects at
# it. Unfold's login template omits the hidden `next` field, which means Django
# falls back to these - and the stock default (`/accounts/profile/`) is a route
# this project does not serve, so signing in would land on a 404.
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/admin/login/"

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = env.str("DJANGO_LANGUAGE_CODE")
TIME_ZONE = env.str("DJANGO_TIME_ZONE")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / env.str("STATIC_ROOT")
STATICFILES_DIRS = [BASE_DIR / "static"]

# Uploaded media goes either to the local disk or to S3 depending on `USE_S3`.
# `storage.py` owns that decision and returns MEDIA_URL / MEDIA_ROOT / STORAGES.
globals().update(build_media_storage(env, BASE_DIR))

# Upload guard rails - a single image should never exceed this.
MAX_UPLOAD_SIZE_MB = 10

# ---------------------------------------------------------------------------
# CORS - which frontends may call the API
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    # Reads are public (the website consumes them anonymously); writes require a
    # token - that is what the MCP server authenticates with.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.api.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": f"{SITE_NAME} Backend API",
    "DESCRIPTION": (
        "Content API for events, blogs and faculty profiles. "
        "Read endpoints are public; write endpoints require a token "
        "(`Authorization: Token <key>`)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# ---------------------------------------------------------------------------
# CKEditor - rich text content
# ---------------------------------------------------------------------------

CKEDITOR_UPLOAD_PATH = "uploads/ckeditor/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_RESTRICT_BY_USER = False
CKEDITOR_BROWSE_SHOW_DIRS = True

# CKEditor 4 shows an "this version is not secure" notification *inside the
# editor body* and logs it to the console. It is aimed at developers, but it is
# content editors who would see the red banner in the middle of their text
# area, so it is turned off in both toolbars below via `versionCheck`.
#
# Suppressing the notice does not change the underlying fact: django-ckeditor
# bundles CKEditor 4, which is end-of-life. See docs/architecture.md for the
# migration options.
CKEDITOR_CONFIGS = {
    "default": {
        "skin": "moono-lisa",
        "versionCheck": False,
        "toolbar": "MBU",
        "toolbar_MBU": [
            {"name": "styles", "items": ["Format", "Styles"]},
            {
                "name": "basicstyles",
                "items": ["Bold", "Italic", "Underline", "Strike", "Superscript", "Subscript", "-", "RemoveFormat"],
            },
            {
                "name": "paragraph",
                "items": ["NumberedList", "BulletedList", "-", "Outdent", "Indent", "-", "Blockquote",
                          "JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"],
            },
            {"name": "links", "items": ["Link", "Unlink", "Anchor"]},
            {"name": "insert", "items": ["Image", "Table", "HorizontalRule", "SpecialChar"]},
            {"name": "colors", "items": ["TextColor", "BGColor"]},
            {"name": "tools", "items": ["Maximize", "ShowBlocks", "Source"]},
            {"name": "clipboard", "items": ["Undo", "Redo", "-", "Cut", "Copy", "Paste", "PasteText", "PasteFromWord"]},
        ],
        "height": 400,
        "width": "100%",
        "toolbarCanCollapse": True,
        "removePlugins": "exportpdf",
        "extraPlugins": ",".join(["uploadimage", "autolink", "widget", "dialog"]),
        "filebrowserUploadMethod": "form",
        # Allow the semantic markup a CMS realistically needs.
        "allowedContent": True,
        "contentsCss": [],
    },
    # A lighter editor for short blocks such as faculty section bodies.
    "compact": {
        "skin": "moono-lisa",
        "versionCheck": False,
        "toolbar": "Compact",
        "toolbar_Compact": [
            {"name": "basicstyles", "items": ["Bold", "Italic", "Underline", "-", "RemoveFormat"]},
            {"name": "paragraph", "items": ["NumberedList", "BulletedList", "-", "Blockquote"]},
            {"name": "links", "items": ["Link", "Unlink"]},
            {"name": "insert", "items": ["Table", "HorizontalRule"]},
            {"name": "tools", "items": ["Maximize", "Source"]},
        ],
        "height": 240,
        "width": "100%",
        "allowedContent": True,
        # Same as the default config: exportpdf is a paid cloud service and
        # logs a console warning on every editor instance without a token.
        "removePlugins": "exportpdf",
    },
}

# ---------------------------------------------------------------------------
# Unfold - admin dashboard UI
# ---------------------------------------------------------------------------


def _navigation_visible(request):
    """Sidebar entries are only shown to staff members."""
    return request.user.is_active and request.user.is_staff


UNFOLD = {
    "SITE_TITLE": f"{SITE_NAME} Admin",
    "SITE_HEADER": SITE_NAME,
    "SITE_SUBHEADER": "Content Management",
    "SITE_URL": "/",
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "ENVIRONMENT": "mbu_backend.settings.unfold_callbacks.environment_callback",
    "DASHBOARD_CALLBACK": "apps.core.admin.dashboard.dashboard_callback",
    "BORDER_RADIUS": "8px",
    "COLORS": {
        # Maroon brand scale (space separated RGB, the format Unfold expects).
        "primary": {
            "50": "253 242 243",
            "100": "254 226 229",
            "200": "254 205 211",
            "300": "253 164 175",
            "400": "251 113 133",
            "500": "225 77 96",
            "600": "190 45 66",
            "700": "158 30 50",
            "800": "131 27 45",
            "900": "112 26 43",
            "950": "63 10 20",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Overview",
                "separator": False,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                        "permission": _navigation_visible,
                    },
                ],
            },
            {
                "title": "Content",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Events",
                        "icon": "event",
                        "link": reverse_lazy("admin:events_event_changelist"),
                        "permission": _navigation_visible,
                    },
                    {
                        "title": "Blogs",
                        "icon": "article",
                        "link": reverse_lazy("admin:blogs_blog_changelist"),
                        "permission": _navigation_visible,
                    },
                    {
                        "title": "Faculty",
                        "icon": "groups",
                        "link": reverse_lazy("admin:faculty_faculty_changelist"),
                        "permission": _navigation_visible,
                    },
                ],
            },
            {
                "title": "Taxonomy",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Departments",
                        "icon": "account_tree",
                        "link": reverse_lazy("admin:core_department_changelist"),
                        "permission": _navigation_visible,
                    },
                    {
                        "title": "Courses",
                        "icon": "school",
                        "link": reverse_lazy("admin:core_course_changelist"),
                        "permission": _navigation_visible,
                    },
                    {
                        "title": "Event Categories",
                        "icon": "sell",
                        "link": reverse_lazy("admin:events_eventcategory_changelist"),
                        "permission": _navigation_visible,
                    },
                    {
                        "title": "Blog Categories",
                        "icon": "label",
                        "link": reverse_lazy("admin:blogs_blogcategory_changelist"),
                        "permission": _navigation_visible,
                    },
                    {
                        "title": "Designations",
                        "icon": "badge",
                        "link": reverse_lazy("admin:faculty_designation_changelist"),
                        "permission": _navigation_visible,
                    },
                ],
            },
            {
                "title": "Access",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "permission": _navigation_visible,
                    },
                    {
                        "title": "Groups",
                        "icon": "shield_person",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": _navigation_visible,
                    },
                    {
                        "title": "API Tokens",
                        "icon": "key",
                        "link": reverse_lazy("admin:authtoken_tokenproxy_changelist"),
                        "permission": _navigation_visible,
                    },
                ],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Logging - never swallow an error silently
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "mcp_server": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
