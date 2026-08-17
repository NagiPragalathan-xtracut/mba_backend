"""Event and its image gallery."""

from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models, transaction

from apps.core.fields import SVGImageField
from apps.core.models import ContentBase, Department, OrderedModel
from apps.core.utils.dates import iso_date
from apps.core.utils.text import summarise

from .category import EventCategory


class Event(ContentBase):
    """
    A single event or achievement.

    The featured image is not a column on this model: it is whichever row in
    the gallery (`EventImage`) carries ``is_featured``. That is what the brief
    asked for - the highlight image is *chosen from the uploaded photos* rather
    than uploaded a second time - and it keeps a single copy of each file.
    """

    title = models.CharField(max_length=255, help_text="Event name as shown on the website.")
    category = models.ForeignKey(
        EventCategory,
        on_delete=models.PROTECT,
        related_name="events",
        help_text="Upcoming, Achievements, ...",
    )
    departments = models.ManyToManyField(
        Department,
        related_name="events",
        blank=True,
        help_text="Departments this event belongs to. Leave empty for university-wide events.",
    )
    summary = models.TextField(
        blank=True, default="",
        help_text="Short teaser shown on listing cards. Generated from the content when blank.",
    )
    content = RichTextUploadingField(help_text="Full event description.")

    event_date = models.DateField(null=True, blank=True, help_text="When the event takes place / took place.")
    end_date = models.DateField(null=True, blank=True, help_text="Last day, for multi-day events.")
    venue = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["display_order", "-event_date", "-created_at"]
        verbose_name = "Event"
        verbose_name_plural = "Events"
        indexes = [
            models.Index(fields=["is_published", "display_order"]),
            models.Index(fields=["category", "is_published"]),
        ]

    def __str__(self) -> str:
        return self.title

    # ------------------------------------------------------------------
    # Featured image
    # ------------------------------------------------------------------

    @property
    def featured_image(self):
        """The gallery image flagged as featured, else the first one, else None."""
        if not self.pk:
            # Reverse relations are unusable before the row exists, and a brand
            # new event has no gallery yet anyway.
            return None
        images = list(self.images.all())
        for image in images:
            if image.is_featured:
                return image
        return images[0] if images else None

    @property
    def featured_image_url(self) -> str:
        image = self.featured_image
        return image.image.url if image and image.image else ""

    def save(self, *args, **kwargs):
        # A blank summary is derived from the body so listing cards always have
        # something to show.
        if not self.summary:
            self.summary = summarise(self.content, 220)
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # SEO hooks (see apps.core.models.seo.SEOMixin)
    # ------------------------------------------------------------------

    def seo_headline(self) -> str:
        return self.title

    def seo_summary(self) -> str:
        return self.summary or self.content

    def seo_image_url(self) -> str:
        return self.featured_image_url

    def seo_path(self) -> str:
        return f"/events/{self.slug}/"

    def seo_keyword_sources(self) -> list[str]:
        sources = [self.title]
        if self.pk:
            # M2M rows only exist once the instance has a primary key.
            sources.append(self.category.name if self.category_id else "")
            sources.extend(department.name for department in self.departments.all())
        return [source for source in sources if source]

    def seo_schema_type(self) -> str:
        return "Event"

    def seo_schema_extra(self) -> dict:
        extra = {}
        if self.event_date:
            extra["startDate"] = iso_date(self.event_date)
        if self.end_date:
            extra["endDate"] = iso_date(self.end_date)
        if self.venue:
            extra["location"] = {"@type": "Place", "name": self.venue}
        return extra


class EventImage(OrderedModel):
    """One photo in an event's gallery."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="images")
    image = SVGImageField(upload_to="events/gallery/", help_text="Photo file.")
    alt = models.CharField(max_length=255, blank=True, default="", help_text="Alt text for accessibility and SEO.")
    caption = models.CharField(max_length=500, blank=True, default="")
    is_featured = models.BooleanField(
        default=False,
        help_text="Use this photo as the event's highlight image. Only one photo per event can be featured.",
    )

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Event Image"
        verbose_name_plural = "Event Images"
        constraints = [
            # Database-level guarantee that an event never has two featured
            # photos, whatever writes the rows (admin, API or a data import).
            models.UniqueConstraint(
                fields=["event"],
                condition=models.Q(is_featured=True),
                name="unique_featured_image_per_event",
            )
        ]

    def __str__(self) -> str:
        return f"{self.event.title} - {self.alt or self.image.name.rsplit('/', 1)[-1]}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_featured:
                # Demote the previous winner first; the unique constraint above
                # would otherwise reject this row.
                EventImage.objects.filter(event=self.event, is_featured=True).exclude(pk=self.pk).update(
                    is_featured=False
                )
            elif not EventImage.objects.filter(event=self.event, is_featured=True).exclude(pk=self.pk).exists():
                # First photo uploaded for the event becomes the highlight so
                # listing pages are never image-less.
                self.is_featured = True

            if not self.alt:
                self.alt = self.caption or self.event.title

            super().save(*args, **kwargs)
