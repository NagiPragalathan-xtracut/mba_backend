"""Faculty profile, its repeatable content sections and its banner gallery."""

from ckeditor.fields import RichTextField
from django.core.validators import RegexValidator
from django.db import models

from apps.core.fields import SVGImageField
from apps.core.models import ContentBase, Department, OrderedModel
from apps.core.utils.text import summarise

from .designation import Designation

phone_validator = RegexValidator(
    regex=r"^[0-9+()\-\s]{6,20}$",
    message="Enter a valid phone number (digits, spaces and + ( ) - only).",
)


class Faculty(ContentBase):
    """
    A staff member's public profile.

    Profile *content* is deliberately not a fixed set of columns. Different
    departments describe their staff differently - some want Publications and
    Patents, others want Industry Experience - so the long-form parts live in
    :class:`FacultySection` rows an editor adds with the "+" button in the
    admin. Only the structured, queryable fields are columns here.
    """

    # The profile is identified by a person's name, not a "title".
    SLUG_SOURCE_FIELD = "name"

    name = models.CharField(max_length=255, help_text="Full name as it should appear publicly.")
    image = SVGImageField(
        upload_to="faculty/photos/", blank=True, null=True,
        help_text="Profile photo. Portrait orientation works best.",
    )
    external_image_url = models.URLField(
        max_length=500, blank=True, default="",
        help_text=(
            "Optional CDN address of the photo, used when no file is uploaded above. "
            "Lets existing photos stay on the university CDN instead of being re-uploaded."
        ),
    )
    image_alt = models.CharField(max_length=255, blank=True, default="", help_text="Alt text for the photo.")

    designation = models.ForeignKey(
        Designation, on_delete=models.PROTECT, related_name="faculty_members",
        help_text="Job title.",
    )
    departments = models.ManyToManyField(
        Department, related_name="faculty_members", blank=True,
        help_text="Departments this person belongs to. More than one is allowed.",
    )

    qualification = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Degrees and certifications, e.g. 'Ph.D., M.Tech, B.Tech'.",
    )
    mail_id = models.EmailField(blank=True, default="", help_text="Optional. Shown publicly when filled.")
    phone_number = models.CharField(
        max_length=20, blank=True, default="", validators=[phone_validator],
        help_text="Optional. Shown publicly when filled.",
    )
    profile_link = models.URLField(blank=True, default="", help_text="Optional personal site, Scholar or ORCID profile.")

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Faculty"
        verbose_name_plural = "Faculty"
        indexes = [
            models.Index(fields=["is_published", "display_order"]),
        ]

    def __str__(self) -> str:
        designation = self.designation.name if self.designation_id else ""
        return f"{self.name} - {designation}" if designation else self.name

    @property
    def image_url(self) -> str:
        """The photo to display: an uploaded file wins over the CDN address."""
        if self.image:
            return self.image.url
        return self.external_image_url

    @property
    def department_names(self) -> list[str]:
        return [department.name for department in self.departments.all()] if self.pk else []

    def save(self, *args, **kwargs):
        if not self.image_alt:
            self.image_alt = self.name
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # SEO hooks
    # ------------------------------------------------------------------

    def seo_headline(self) -> str:
        return self.name

    def seo_summary(self) -> str:
        """Build a description from the qualification and the first section."""
        parts = []
        if self.designation_id:
            parts.append(self.designation.name)
        if self.qualification:
            parts.append(self.qualification)
        if self.pk:
            first_section = self.sections.first()
            if first_section:
                parts.append(summarise(first_section.content, 160))
        return " | ".join(part for part in parts if part)

    def seo_image_url(self) -> str:
        return self.image_url

    def seo_path(self) -> str:
        return f"/faculty/{self.slug}/"

    def seo_keyword_sources(self) -> list[str]:
        sources = [self.name, self.qualification]
        if self.designation_id:
            sources.append(self.designation.name)
        if self.pk:
            sources.extend(self.department_names)
        return [source for source in sources if source]

    def seo_schema_type(self) -> str:
        return "Person"

    def seo_schema_extra(self) -> dict:
        extra = {}
        if self.designation_id:
            extra["jobTitle"] = self.designation.name
        if self.mail_id:
            extra["email"] = self.mail_id
        if self.phone_number:
            extra["telephone"] = self.phone_number
        if self.profile_link:
            extra["sameAs"] = [self.profile_link]
        if self.pk and self.department_names:
            extra["affiliation"] = [
                {"@type": "Organization", "name": name} for name in self.department_names
            ]
        return extra


class FacultySection(OrderedModel):
    """
    One titled, rich-text block on a faculty profile.

    This is the repeatable "heading + content" set from the brief: an editor
    clicks "+" in the admin to add as many as the person needs (Biography,
    Publications, Awards, Workshops, Projects, ...), in any order.
    """

    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="sections")
    heading = models.CharField(max_length=255, help_text="Section title, e.g. 'Publications'.")
    content = RichTextField(config_name="compact", help_text="Section body.")
    is_visible = models.BooleanField(default=True, help_text="Untick to hide this section without deleting it.")

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Profile Section"
        verbose_name_plural = "Profile Sections"
        constraints = [
            # The same heading twice on one profile is always an editing mistake.
            models.UniqueConstraint(fields=["faculty", "heading"], name="unique_section_heading_per_faculty"),
        ]

    def __str__(self) -> str:
        return f"{self.faculty.name} - {self.heading}"


class FacultyBanner(OrderedModel):
    """A wide image for the profile page header or photo strip."""

    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="banners")
    image = SVGImageField(upload_to="faculty/banners/")
    alt = models.CharField(max_length=255, blank=True, default="", help_text="Alt text for the banner.")

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Faculty Banner"
        verbose_name_plural = "Faculty Banners"

    def __str__(self) -> str:
        return f"Banner for {self.faculty.name}"

    def save(self, *args, **kwargs):
        if not self.alt:
            self.alt = self.faculty.name
        super().save(*args, **kwargs)
