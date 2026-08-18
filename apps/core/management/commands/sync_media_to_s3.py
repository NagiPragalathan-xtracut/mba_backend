"""
One-off migration of existing local uploads into the configured S3 bucket.

Switching ``USE_S3`` on only changes where *new* uploads go - files already
sitting in ``MEDIA_ROOT`` stay on disk and their URLs start 404ing. This
command walks the local media directory and uploads every file to the same
relative key, so existing events, blogs and faculty keep their images.

Usage::

    python manage.py sync_media_to_s3 --dry-run   # list what would be uploaded
    python manage.py sync_media_to_s3             # upload missing files
    python manage.py sync_media_to_s3 --overwrite # re-upload everything
"""

from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Upload files from the local MEDIA_ROOT into the configured S3 bucket."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be uploaded without transferring anything.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Re-upload files that already exist in the bucket.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_S3", False):
            raise CommandError(
                "USE_S3 is not enabled - the default storage is the local disk, "
                "so there is nothing to sync. Set USE_S3=True in .env first."
            )

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.is_dir():
            raise CommandError(f"MEDIA_ROOT does not exist: {media_root}")

        dry_run = options["dry_run"]
        overwrite = options["overwrite"]
        uploaded = skipped = failed = 0

        for path in sorted(p for p in media_root.rglob("*") if p.is_file()):
            # The storage backend adds its own `media/` prefix, so the key is
            # the path relative to MEDIA_ROOT, with forward slashes on Windows.
            key = path.relative_to(media_root).as_posix()

            if not overwrite and default_storage.exists(key):
                skipped += 1
                self.stdout.write(f"  skip (exists)  {key}")
                continue

            if dry_run:
                uploaded += 1
                self.stdout.write(f"  would upload   {key}")
                continue

            try:
                with path.open("rb") as handle:
                    # `save` would rename on collision; `_save` via an explicit
                    # delete keeps the key stable when --overwrite is used.
                    if overwrite and default_storage.exists(key):
                        default_storage.delete(key)
                    default_storage.save(key, handle)
            except Exception as exc:  # noqa: BLE001 - report and keep going
                failed += 1
                self.stderr.write(self.style.ERROR(f"  FAILED         {key}: {exc}"))
                continue

            uploaded += 1
            self.stdout.write(f"  uploaded       {key}")

        summary = f"{uploaded} uploaded, {skipped} skipped, {failed} failed"
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run: {summary} (nothing transferred)"))
        elif failed:
            self.stdout.write(self.style.ERROR(f"Finished with errors: {summary}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Media sync complete: {summary}"))
