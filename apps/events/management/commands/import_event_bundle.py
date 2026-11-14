"""
Import hand-curated events from a bundle directory.

A bundle is a folder holding ``manifest.json`` plus the photos it references::

    manifest.json
    images/<key>/01.jpeg, 02.png ...

``manifest.json`` is a list of events::

    [{
      "slug": "harmonia-2026-alumni-meet",
      "title": "Harmonia 2026 - A Celebration of Bonds Beyond Graduation",
      "category": "events",                       # EventCategory slug
      "departments": ["school-of-management"],    # Department slugs
      "courses": ["mba"],                         # Course slugs (optional)
      "event_date": "2026-10-02", "end_date": null,
      "start_time": "10:00", "end_time": "11:30",  # optional
      "venue": "TRP Auditorium",
      "summary": "One-line teaser for listing cards.",
      "content": "<p>...</p>",
      "images": ["images/harmonia/08.jpeg", ...],  # first one is featured
      "is_published": true,                        # optional, default true
      "display_order": 0                           # optional, default 0
    }]

    python manage.py import_event_bundle path/to/bundle --dry-run
    python manage.py import_event_bundle path/to/bundle

Safe to run repeatedly: events are keyed on ``slug`` and updated in place, and
their gallery is replaced with freshly compressed photos. An existing event
with the same slug but a different title is left alone, so a bundle can never
overwrite an unrelated event.
"""

import json
from datetime import date, time
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import Course, Department
from apps.events.models import Event, EventCategory, EventImage

from .import_srm_events import compress_image


def _date(value):
    return date.fromisoformat(value) if value else None


def _time(value):
    return time.fromisoformat(value) if value else None


class Command(BaseCommand):
    help = "Import curated events (manifest.json + photos) from a bundle directory."

    def add_arguments(self, parser):
        parser.add_argument("bundle", help="Directory holding manifest.json and the photos.")
        parser.add_argument("--only", action="append", default=[], help="Import only this slug (repeatable).")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing anything.")

    def handle(self, *args, bundle, only, dry_run, **options):
        root = Path(bundle)
        try:
            entries = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise CommandError(f"Cannot read {root / 'manifest.json'}: {error}") from error
        if only:
            entries = [entry for entry in entries if entry["slug"] in only]

        categories = {c.slug: c for c in EventCategory.objects.all()}
        departments = {d.slug: d for d in Department.objects.all()}
        courses = {c.slug: c for c in Course.objects.all()}

        # Validate everything before writing anything.
        problems = []
        for entry in entries:
            label = entry.get("slug", "?")
            for key in ("slug", "title", "category", "content"):
                if not entry.get(key):
                    problems.append(f"{label}: missing {key}")
            if entry.get("category") not in categories:
                problems.append(f"{label}: unknown category {entry.get('category')!r}")
            problems += [f"{label}: unknown department {s!r}" for s in entry.get("departments", []) if s not in departments]
            problems += [f"{label}: unknown course {s!r}" for s in entry.get("courses", []) if s not in courses]
            problems += [f"{label}: missing photo {p}" for p in entry.get("images", []) if not (root / p).is_file()]
        if problems:
            raise CommandError("Bundle has problems:\n  " + "\n  ".join(problems))

        self.bytes_in = self.bytes_out = 0
        created = updated = skipped = 0
        for entry in entries:
            event = Event.objects.filter(slug=entry["slug"]).first()
            if event and event.title != entry["title"]:
                self.stderr.write(f"  {entry['slug']}: slug belongs to '{event.title}', skipped")
                skipped += 1
                continue

            is_new = event is None
            photos = self._compress([(root / p).read_bytes() for p in entry.get("images", [])])
            if not dry_run:
                with transaction.atomic():
                    event = event or Event(slug=entry["slug"])
                    event.title = entry["title"]
                    event.category = categories[entry["category"]]
                    event.summary = entry.get("summary", "")
                    event.content = entry["content"]
                    event.event_date = _date(entry.get("event_date"))
                    event.end_date = _date(entry.get("end_date"))
                    event.start_time = _time(entry.get("start_time"))
                    event.end_time = _time(entry.get("end_time"))
                    event.venue = entry.get("venue", "")[:255]
                    event.is_published = entry.get("is_published", True)
                    event.display_order = entry.get("display_order", 0)
                    event.save()
                    event.departments.set([departments[s] for s in entry.get("departments", [])])
                    event.courses.set([courses[s] for s in entry.get("courses", [])])
                    self._replace_gallery(event, photos)

            created += is_new
            updated += not is_new
            self.stdout.write(
                f"  {'created' if is_new else 'updated'} {entry['slug']} | {entry.get('event_date') or '-'} | "
                f"{len(photos)} photos"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Done{' (dry run, nothing written)' if dry_run else ''}: {created} created, {updated} updated, "
            f"{skipped} skipped. Photos {self.bytes_in / 2**20:.1f} MB -> {self.bytes_out / 2**20:.1f} MB."
        ))

    def _compress(self, images: list[bytes]) -> list[bytes]:
        out = []
        for data in images:
            try:
                compressed = compress_image(data)
            except OSError as error:
                self.stderr.write(f"    unreadable image skipped: {error}")
                continue
            self.bytes_in += len(data)
            self.bytes_out += len(compressed)
            out.append(compressed)
        return out

    def _replace_gallery(self, event, photos: list[bytes]):
        for old in event.images.all():
            old.image.delete(save=False)
            old.delete()
        stem = event.slug[:60].rstrip("-")
        for number, data in enumerate(photos, start=1):
            EventImage.objects.create(
                event=event,
                image=ContentFile(data, name=f"{stem}-{number:02d}.jpg"),
                alt=f"{event.title[:230]} - photo {number}",
                is_featured=number == 1,
                display_order=number * 10,
            )
