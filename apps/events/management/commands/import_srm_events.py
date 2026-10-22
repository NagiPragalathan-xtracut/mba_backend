"""
Import an SRM events export (a zip scraped from fsh.srmrmp.edu.in) as events.

Each zip holds an ``events_index.csv`` plus one folder per event::

    events_index.csv                       No, Event Title, Date, Venue, Images, Source URL, Status
    01 - <title>/content.txt               scraped page text
    01 - <title>/images/01.jpg, 02.jpg ...

Every photo is compressed on the way in (EXIF-rotated, flattened to RGB,
longest side capped at ``MAX_IMAGE_SIDE``, re-encoded as progressive JPEG), so
the originals - often multi-megabyte phone shots - never reach media storage.

    python manage.py import_srm_events SRM_MBA_Events.zip --prefix mba --course mba
    python manage.py import_srm_events SRM_FDP_Events.zip --prefix fdp
    python manage.py import_srm_events SRM_BBA_Events.zip --prefix bba --images-only

Safe to run repeatedly: events are keyed on ``srm-<prefix>-<title>`` and
updated in place, and their gallery is replaced. ``--images-only`` leaves the
event text alone and only swaps the gallery for freshly compressed photos -
use it for events that were imported earlier and edited since.
"""

import csv
import html
import io
import re
import zipfile
from collections import defaultdict
from datetime import date, time

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from PIL import Image, ImageOps

from apps.core.models import Course, Department
from apps.core.utils.text import clean_whitespace
from apps.events.models import Event, EventCategory, EventImage

MAX_IMAGE_SIDE = 1600
JPEG_QUALITY = 75

DEPARTMENT_SLUG = "school-of-management"
CATEGORY_SLUG = "events"

#: Status the scraper writes when the event page itself was a 404. Only the
#: listing card's title and thumbnail exist, so the event is kept unpublished.
CARD_ONLY_STATUS = "card only"

#: Lines the scraper picked up from the page chrome rather than the article.
_NOISE_RE = re.compile(r"^(UNCODE\.|PrevNext$)")

#: ``Label: value`` lines whose value is already stored in a model field.
_FIELD_LABELS = {"event title", "title", "event", "date", "time", "timing", "venue", "event name"}

_HEADING_WORDS = re.compile(
    r"^(summary|description|objective|outcome|highlights?|key (takeaways|highlights|achievements)|"
    r"conclusion|background|recognition|sessions?|agenda|about)",
    re.IGNORECASE,
)

_MONTHS = {
    name: number
    for number, names in enumerate(
        [("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",),
         ("jun", "june"), ("jul", "july"), ("aug", "august"), ("sep", "sept", "september"),
         ("oct", "october"), ("nov", "november"), ("dec", "december")],
        start=1,
    )
    for name in names
}
_MONTH = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_ORD = r"(?:st|nd|rd|th)?"
_RANGE_SEP = r"\s*(?:-|–|to|&)\s*"

# 9th -14th October 2023
_DAY_RANGE_MONTH_RE = re.compile(rf"\b(\d{{1,2}}){_ORD}{_RANGE_SEP}(\d{{1,2}}){_ORD}\s+{_MONTH},?\s+(\d{{4}})", re.I)
# 28 January 2026 / 20th Jan, 2026
_DAY_MONTH_RE = re.compile(rf"\b(\d{{1,2}}){_ORD}\s+(?:of\s+)?{_MONTH},?\s+(\d{{4}})", re.I)
# January 9, 2026
_MONTH_DAY_RE = re.compile(rf"\b{_MONTH}\s+(\d{{1,2}}){_ORD},?\s+(\d{{4}})", re.I)
# 01-07-2025 / 18.02. 2025 / 27/06/2025 / 11.8.25
_NUMERIC_RE = re.compile(r"\b(\d{1,2})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{4}|\d{2})\b")

# 11.00 am / 10:00 A.M. / 6.00 Pm / 4 pm
_TIME_RE = re.compile(r"\b(\d{1,2})(?:[.:](\d{2}))?\s*([ap])\.?\s*m\b\.?", re.I)


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------


def _safe_date(year, month, day):
    year = int(year)
    if year < 100:
        year += 2000
    try:
        return date(year, int(month), int(day))
    except (TypeError, ValueError):
        return None


def parse_dates(text: str) -> tuple[date | None, date | None]:
    """First date (and range end, when given) found in ``text``."""
    if not text:
        return None, None

    match = _DAY_RANGE_MONTH_RE.search(text)
    if match:
        month = _MONTHS[match.group(3).lower()]
        start = _safe_date(match.group(4), month, match.group(1))
        end = _safe_date(match.group(4), month, match.group(2))
        if start and end and end > start:
            return start, end

    found = []
    for regex, order in ((_NUMERIC_RE, "dmy"), (_DAY_MONTH_RE, "dMy"), (_MONTH_DAY_RE, "Mdy")):
        for match in regex.finditer(text):
            if order == "dmy":
                parsed = _safe_date(match.group(3), match.group(2), match.group(1))
            elif order == "dMy":
                parsed = _safe_date(match.group(3), _MONTHS[match.group(2).lower()], match.group(1))
            else:
                parsed = _safe_date(match.group(3), _MONTHS[match.group(1).lower()], match.group(2))
            if parsed:
                found.append((match.start(), parsed))
    if not found:
        return None, None

    found.sort()
    start = found[0][1]
    # "22-07-2025 to 26-07-2025": a second date right after the first is the end.
    end = found[1][1] if len(found) > 1 and found[1][1] > start and found[1][0] - found[0][0] < 40 else None
    return start, end


def parse_times(text: str) -> tuple[time | None, time | None]:
    """Start and end clock time found in ``text``."""
    times = []
    for match in _TIME_RE.finditer(text or ""):
        hour, minute = int(match.group(1)), int(match.group(2) or 0)
        if not (1 <= hour <= 12 and minute < 60):
            continue
        if match.group(3).lower() == "p" and hour != 12:
            hour += 12
        elif match.group(3).lower() == "a" and hour == 12:
            hour = 0
        times.append(time(hour, minute))
        if len(times) == 2:
            break
    start = times[0] if times else None
    end = times[1] if len(times) > 1 and times[1] > times[0] else None
    return start, end


def _split_label(line: str) -> tuple[str, str] | None:
    """``("Venue", "Gallery Hall")`` for a ``Venue: Gallery Hall`` line."""
    match = re.match(r"^([A-Za-z][A-Za-z .&/()'’-]{1,40}?)\s*[:\-–]\s*(.*)$", line)
    if not match or ":" not in line[: len(match.group(1)) + 3]:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _heading(text: str) -> str:
    text = text.rstrip(":").strip()
    return text.title() if text.isupper() else text


def parse_content(raw: str) -> dict:
    """
    Split a scraped ``content.txt`` into its header and an HTML body.

    Returns ``{"header": {...}, "labels": {...}, "html": str, "text": str}``,
    where ``labels`` holds the ``Label: value`` lines (lower-cased keys) and
    ``text`` is the body as plain text for date/time sniffing.
    """
    header_part, _, body = raw.replace("\r\n", "\n").partition("\n\n")
    header = {}
    for line in header_part.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            header[key.strip().lower()] = value.strip()

    lines = [clean_whitespace(line) for line in body.split("\n")]
    lines = [line for line in lines if line and not _NOISE_RE.match(line)]

    labels: dict[str, str] = {}
    blocks: list[str] = []
    bullets: list[str] = []

    def flush_bullets():
        if bullets:
            blocks.append("<ul>" + "".join(f"<li>{html.escape(b)}</li>" for b in bullets) + "</ul>")
            bullets.clear()

    for line in lines:
        if line.startswith("NOTE: The \"Read More\" link"):
            continue
        if line[0] in "•●▪◦·*" and len(line) > 1:
            bullets.append(line[1:].strip())
            continue
        flush_bullets()

        label = _split_label(line)
        if label and label[1]:
            key = label[0].lower()
            labels.setdefault(key, label[1])
            if key in _FIELD_LABELS:
                continue
            blocks.append(f"<p><strong>{html.escape(_heading(label[0]))}:</strong> {html.escape(label[1])}</p>")
            continue

        is_heading = len(line) <= 60 and not line.endswith(".") and (
            line.endswith(":") or _HEADING_WORDS.match(line)
        )
        if is_heading:
            blocks.append(f"<h3>{html.escape(_heading(line))}</h3>")
        else:
            blocks.append(f"<p>{html.escape(line)}</p>")
    flush_bullets()

    return {"header": header, "labels": labels, "html": "\n".join(blocks), "text": "\n".join(lines)}


def clean_title(title: str, parsed: dict) -> str:
    """CSV title, falling back to the page title; drops the scraper's site prefix."""
    title = clean_whitespace(title)
    if not title:
        page_title = parsed["header"].get("page title", "")
        title = "" if page_title.startswith("(") else page_title
    title = re.sub(r"^COLLEGE OF MANAGEMENT\s*", "", title).strip()
    if not title:
        # "COLLEGE OF MANAGEMENT" alone: the real name follows "Organises".
        lines = parsed["text"].split("\n")
        for index, line in enumerate(lines[:-1]):
            if line.lower() in {"organises", "organizes", "organised", "organized"}:
                title = lines[index + 1]
                break
    return title[:255]


def compress_image(data: bytes) -> bytes:
    """Photo ``data`` re-encoded as a web-sized progressive JPEG."""
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode != "RGB":
            rgba = image.convert("RGBA")
            image = Image.new("RGB", rgba.size, "white")
            image.paste(rgba, mask=rgba.getchannel("A"))
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)
        output = io.BytesIO()
        image.save(output, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return output.getvalue()


def read_export(path: str) -> list[dict]:
    """Rows of the export's index, each with its ``content`` text and ``images`` bytes."""
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise CommandError(f"Cannot open {path}: {error}") from error

    # Folder names were written with a non-UTF-8 code page, so folders are
    # matched on their leading number ("07 - ...") rather than their name.
    folders: dict[int, dict] = defaultdict(lambda: {"content": "", "images": []})
    index_csv = None
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.filename == "events_index.csv":
                index_csv = archive.read(info).decode("utf-8-sig")
                continue
            match = re.match(r"^(\d+) - [^/]*/(content\.txt|images/(.+))$", info.filename)
            if not match:
                continue
            folder = folders[int(match.group(1))]
            if match.group(2) == "content.txt":
                folder["content"] = archive.read(info).decode("utf-8", errors="replace")
            else:
                folder["images"].append((match.group(3), archive.read(info)))

    if index_csv is None:
        raise CommandError(f"{path} has no events_index.csv")

    rows = []
    for row in csv.DictReader(io.StringIO(index_csv)):
        folder = folders.get(int(row["No"]), {"content": "", "images": []})
        rows.append({**row, "content": folder["content"], "images": sorted(folder["images"])})
    return rows


# --------------------------------------------------------------------------
# Command
# --------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Import an SRM events export zip, compressing every photo."

    def add_arguments(self, parser):
        parser.add_argument("zip_path", help="Path to the export zip.")
        parser.add_argument("--prefix", required=True, help="Slug namespace, e.g. 'mba' -> srm-mba-<title>.")
        parser.add_argument("--course", action="append", default=[], help="Course slug to tag the events with (repeatable).")
        parser.add_argument(
            "--images-only", action="store_true",
            help="Only replace the gallery of events that already exist; leave their text untouched.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing anything.")

    def handle(self, *args, zip_path, prefix, course, images_only, dry_run, **options):
        self.prefix = slugify(prefix)
        self.dry_run = dry_run
        self.department = Department.objects.filter(slug=DEPARTMENT_SLUG).first()
        self.category = EventCategory.objects.filter(slug=CATEGORY_SLUG).first()
        if self.category is None:
            raise CommandError(f"Event category '{CATEGORY_SLUG}' does not exist. Run `python manage.py migrate` first.")
        self.courses = list(Course.objects.filter(slug__in=course))
        missing = set(course) - {c.slug for c in self.courses}
        if missing:
            raise CommandError(f"Unknown course slug(s): {', '.join(sorted(missing))}")

        rows = read_export(zip_path)
        self.stdout.write(f"{len(rows)} events in {zip_path}")
        self.bytes_in = self.bytes_out = 0
        seen_slugs: set[str] = set()
        created = updated = skipped = 0

        for row in rows:
            parsed = parse_content(row["content"])
            title = clean_title(row["Event Title"], parsed) or parsed["header"].get("event title", "")
            if not title:
                self.stderr.write(f"  #{row['No']}: no title, skipped")
                skipped += 1
                continue
            slug = self._slug(title, seen_slugs)

            if images_only:
                event = self._existing_event(slug, title, seen_slugs)
                if event is None:
                    self.stderr.write(f"  #{row['No']}: '{title}' not found, skipped")
                    skipped += 1
                    continue
                self._replace_gallery(event, row["images"])
                updated += 1
                self.stdout.write(f"  #{row['No']}: {event.slug} ({len(row['images'])} photos)")
                continue

            fields = self._event_fields(row, parsed, title)
            with transaction.atomic():
                event = Event.objects.filter(slug=slug).first()
                is_new = event is None
                if not dry_run:
                    event = event or Event(slug=slug)
                    for name, value in fields.items():
                        setattr(event, name, value)
                    event.save()
                    if self.department:
                        event.departments.set([self.department])
                    event.courses.set(self.courses)
                    self._replace_gallery(event, row["images"])
                else:
                    self._replace_gallery(None, row["images"])
            created += is_new
            updated += not is_new
            self.stdout.write(
                f"  #{row['No']}: {'created' if is_new else 'updated'} {slug} | {fields['event_date'] or '-'} | "
                f"{len(row['images'])} photos{'' if fields['is_published'] else ' | unpublished (card only)'}"
            )

        saved = self.bytes_in - self.bytes_out
        self.stdout.write(self.style.SUCCESS(
            f"Done{' (dry run, nothing written)' if dry_run else ''}: {created} created, {updated} updated, "
            f"{skipped} skipped. Photos {self.bytes_in / 2**20:.1f} MB -> {self.bytes_out / 2**20:.1f} MB "
            f"({saved / max(self.bytes_in, 1):.0%} smaller)."
        ))

    # ------------------------------------------------------------------

    def _slug(self, title: str, seen: set[str]) -> str:
        base = slugify(f"srm-{self.prefix}-{title}")[:90].rstrip("-")
        slug, counter = base, 2
        while slug in seen:
            slug, counter = f"{base}-{counter}", counter + 1
        seen.add(slug)
        return slug

    def _existing_event(self, slug: str, title: str, seen: set[str]):
        """Earlier imports may have slugged differently; fall back to the title."""
        event = Event.objects.filter(slug=slug).first()
        if event:
            return event
        candidates = Event.objects.filter(slug__startswith=f"srm-{self.prefix}-", title__iexact=title).order_by("id")
        for candidate in candidates:
            # Two rows with the same title map onto the events in creation order.
            if candidate.slug not in seen:
                seen.add(candidate.slug)
                return candidate
        return None

    def _event_fields(self, row: dict, parsed: dict, title: str) -> dict:
        labels = parsed["labels"]
        event_date, end_date = parse_dates(row["Date"])
        if not event_date:
            event_date, end_date = parse_dates(labels.get("date", ""))
        if not event_date:
            event_date, end_date = parse_dates(parsed["text"][:1500])
        start_time, end_time = parse_times(labels.get("time") or labels.get("timing") or "")

        venue = clean_whitespace(row["Venue"]) or labels.get("venue", "")
        venue = venue.rstrip(".,").strip()[:255]

        card_only = CARD_ONLY_STATUS in row["Status"].lower()
        content = parsed["html"] or f"<p>{html.escape(title)}</p>"
        return {
            "title": title,
            "category": self.category,
            "content": content,
            "summary": "",  # regenerated from the content by Event.save()
            "event_date": event_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "venue": venue,
            "is_published": not card_only,
        }

    def _replace_gallery(self, event, images: list[tuple[str, bytes]]):
        compressed = []
        for _, data in images:
            try:
                output = compress_image(data)
            except OSError as error:
                self.stderr.write(f"    unreadable image skipped: {error}")
                continue
            self.bytes_in += len(data)
            self.bytes_out += len(output)
            compressed.append(output)

        if event is None or self.dry_run:
            return

        with transaction.atomic():
            for old in event.images.all():
                old.image.delete(save=False)
                old.delete()
            stem = event.slug[:60].rstrip("-")
            for number, data in enumerate(compressed, start=1):
                EventImage.objects.create(
                    event=event,
                    image=ContentFile(data, name=f"{stem}-{number:02d}.jpg"),
                    alt=f"{event.title[:230]} - photo {number}",
                    is_featured=number == 1,
                    display_order=number * 10,
                )
