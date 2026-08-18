"""
Media storage backend selection.

Uploaded media (event photos, blog images, faculty portraits, CKEditor
uploads) lives in one of two places:

* **Local disk** - the default. Files land in ``MEDIA_ROOT`` and Django serves
  them in development. Zero configuration, ideal for local work and tests.
* **Amazon S3** - enabled by setting ``USE_S3=True``. Files are uploaded to the
  bucket under the ``media/`` prefix and served straight from S3 (or a CDN
  domain in front of it), so the application server never touches them.

The switch is a single environment variable, which keeps development friction
at zero while production gets durable, CDN-friendly storage. Static files are
deliberately *not* moved to S3 - WhiteNoise already serves them efficiently
from the application container.
"""

from pathlib import Path

# django-storages backend path. The bucket, credentials and URL behaviour are
# passed as OPTIONS rather than as module-level ``AWS_*`` settings so that all
# storage configuration stays in this one file.
S3_BACKEND = "storages.backends.s3.S3Storage"

# Every object is written under this key prefix. It must match the prefix the
# bucket policy grants public read on (``arn:aws:s3:::<bucket>/media/*``).
S3_LOCATION = "media"


def _s3_public_domain(env) -> str:
    """
    Host that serves the objects.

    Defaults to the bucket's regional S3 endpoint. Set ``AWS_S3_CUSTOM_DOMAIN``
    to a CloudFront distribution or CNAME (e.g. ``cdn.example.edu.in``) to
    serve through a CDN instead - the generated image URLs follow automatically.
    """
    custom = env.str("AWS_S3_CUSTOM_DOMAIN", default="").strip().rstrip("/")
    if custom:
        return custom
    bucket = env.str("AWS_STORAGE_BUCKET_NAME")
    region = env.str("AWS_S3_REGION_NAME")
    return f"{bucket}.s3.{region}.amazonaws.com"


def _s3_config(env) -> dict:
    """Build the S3 storage settings from the environment."""
    domain = _s3_public_domain(env)
    return {
        "USE_S3": True,
        "MEDIA_URL": f"https://{domain}/{S3_LOCATION}/",
        "STORAGES_DEFAULT": {
            "BACKEND": S3_BACKEND,
            "OPTIONS": {
                "bucket_name": env.str("AWS_STORAGE_BUCKET_NAME"),
                "region_name": env.str("AWS_S3_REGION_NAME"),
                "access_key": env.str("AWS_ACCESS_KEY_ID"),
                "secret_key": env.str("AWS_SECRET_ACCESS_KEY"),
                # Non-empty only for S3-compatible providers (Cloudflare R2,
                # DigitalOcean Spaces, MinIO). Empty means real AWS.
                "endpoint_url": env.str("AWS_S3_ENDPOINT_URL", default="") or None,
                "custom_domain": domain,
                "location": S3_LOCATION,
                # Objects are public via the bucket policy, so URLs must be
                # plain and permanent - not time-limited signed links.
                "querystring_auth": False,
                # The bucket has ACLs disabled (Bucket owner enforced); sending
                # an ACL with each upload would be rejected by S3.
                "default_acl": None,
                # Never silently replace an existing file: Django appends a
                # suffix instead, matching local FileSystemStorage behaviour.
                "file_overwrite": False,
                # Long browser/CDN cache - uploaded media is immutable once
                # written because file names are never reused.
                "object_parameters": {"CacheControl": "max-age=86400, public"},
            },
        },
    }


def _local_config() -> dict:
    """Build the local-filesystem storage settings."""
    return {
        "USE_S3": False,
        "MEDIA_URL": "media/",
        "STORAGES_DEFAULT": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }


def build_media_storage(env, base_dir: Path) -> dict:
    """
    Resolve the media storage settings for the current environment.

    Returns a dict of Django settings: ``USE_S3``, ``MEDIA_URL``,
    ``MEDIA_ROOT`` and ``STORAGES``. ``MEDIA_ROOT`` is always defined - even on
    S3 - because temporary uploads and management commands still reference the
    local path.
    """
    config = _s3_config(env) if env.bool("USE_S3", default=False) else _local_config()

    return {
        "USE_S3": config["USE_S3"],
        "MEDIA_URL": config["MEDIA_URL"],
        "MEDIA_ROOT": base_dir / env.str("MEDIA_ROOT"),
        "STORAGES": {
            "default": config["STORAGES_DEFAULT"],
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        },
    }
