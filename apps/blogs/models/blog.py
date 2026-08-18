"""Blog post and its image gallery."""

from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models
from django.utils import timezone

from apps.core.fields import SVGImageField
from apps.core.models import ContentBase, Course, Department, OrderedModel
from apps.core.utils.dates import iso_date
from apps.core.utils.text import strip_html, summarise

from .category import BlogCategory

# Average adult reading speed, used for the "n min read" label.
WORDS_PER_MINUTE = 200


class Blog(ContentBase):
    """A published article."""

    title = models.CharField(max_length=255)
    categories = models.ManyToManyField(
        BlogCategory, related_name="blogs", blank=True,
        help_text="One or more topics this post belongs to.",
    )
    departments = models.ManyToManyField(
        Department, related_name="blogs", blank=True,
        help_text="Departments this post belongs to. Leave empty for university-wide posts.",
    )
    courses = models.ManyToManyField(
        Course, related_name="blogs", blank=True,
        help_text="Programmes this post relates to. Powers the website's Courses filter.",
    )
    summary = models.TextField(
        blank=True, default="",
        help_text="Short teaser shown on listing cards. Generated from the content when blank.",
    )
    content = RichTextUploadingField(help_text="Full article body.")

    # Unlike events, a blog's hero image is uploaded directly rather than picked
    # from the gallery - a post usually has one deliberate cover image.
    featured_image = SVGImageField(
        upload_to="blogs/featured/", blank=True, null=True,
        help_text="Cover image shown on listing cards and social shares.",
    )
    featured_image_alt = models.CharField(max_length=255, blank=True, default="", help_text="Alt text for the cover image.")

    published_date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        help_text="Date shown on the post.",
    )
    author_name = models.CharField(max_length=255, blank=True, default="", help_text="Byline shown on the post.")

    class Meta:
        ordering = ["display_order", "-published_date", "-created_at"]
        verbose_name = "Blog"
        verbose_name_plural = "Blogs"
        indexes = [
            models.Index(fields=["is_published", "-published_date"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def featured_image_url(self) -> str:
        return self.featured_image.url if self.featured_image else ""

    @property
    def reading_time_minutes(self) -> int:
        """Estimated read time in whole minutes, never less than one."""
        word_count = len(strip_html(self.content).split())
        return max(1, round(word_count / WORDS_PER_MINUTE))

    def save(self, *args, **kwargs):
        if not self.summary:
            self.summary = summarise(self.content, 220)
        if not self.featured_image_alt:
            self.featured_image_alt = self.title
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # SEO hooks
    # ------------------------------------------------------------------

    def seo_headline(self) -> str:
        return self.title

    def seo_summary(self) -> str:
        return self.summary or self.content

    def seo_image_url(self) -> str:
        return self.featured_image_url

    def seo_path(self) -> str:
        return f"/blogs/{self.slug}/"

    def seo_keyword_sources(self) -> list[str]:
        sources = [self.title]
        if self.pk:
            sources.extend(category.name for category in self.categories.all())
            sources.extend(department.name for department in self.departments.all())
            sources.extend(course.name for course in self.courses.all())
        return [source for source in sources if source]

    def seo_schema_type(self) -> str:
        return "BlogPosting"

    def seo_schema_extra(self) -> dict:
        extra = {"datePublished": iso_date(self.published_date)}
        if self.updated_at:
            extra["dateModified"] = iso_date(self.updated_at.date())
        if self.author_name:
            extra["author"] = {"@type": "Person", "name": self.author_name}
        return extra


class BlogImage(OrderedModel):
    """An additional image in a blog post's gallery."""

    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="images")
    image = SVGImageField(upload_to="blogs/gallery/")
    alt = models.CharField(max_length=255, blank=True, default="", help_text="Alt text for accessibility and SEO.")
    caption = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Blog Image"
        verbose_name_plural = "Blog Images"

    def __str__(self) -> str:
        return f"{self.blog.title} - {self.alt or self.image.name.rsplit('/', 1)[-1]}"

    def save(self, *args, **kwargs):
        if not self.alt:
            self.alt = self.caption or self.blog.title
        super().save(*args, **kwargs)
