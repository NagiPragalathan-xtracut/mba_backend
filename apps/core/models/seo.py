"""
Reusable SEO metadata.

Every public content type (events, blogs, faculty) needs the same tags: meta
title/description, Open Graph, Twitter cards, canonical URL and schema.org
JSON-LD. Rather than duplicating that logic three times, `SEOMixin` stores the
fields and fills any the editor left blank from a handful of hooks each model
overrides.

**Editor input always wins.** Each auto-filled value is remembered in the
hidden `seo_generated` map, so on the next save the mixin can tell "still the
value we generated" (safe to refresh) apart from "the editor typed this"
(never touched again, only cleaned of stray HTML).

That distinction is what makes `sync_related_seo()` possible: many-to-many
rows - departments, categories - are written *after* the object itself, so
keywords and schema have to be recomputed once relations exist.
"""

import json

from django.conf import settings
from django.db import models

from apps.core.utils.text import clean_whitespace, strip_html, summarise

META_TITLE_LIMIT = 70
META_DESCRIPTION_LIMIT = 160
OG_DESCRIPTION_LIMIT = 200

#: SEO fields whose value depends on many-to-many relations.
RELATION_DEPENDENT_FIELDS = ("keywords", "schema_json")

#: Every column this mixin writes to on save. Callers that pass
#: ``update_fields`` must include these, or the generated values are dropped
#: before they reach the database - see ``ContentBase.save()``.
SEO_MANAGED_FIELDS = (
    "meta_title", "meta_description", "keywords", "canonical_url", "author",
    "og_title", "og_description", "og_image",
    "twitter_card", "twitter_title", "twitter_description", "twitter_image",
    "schema_json", "seo_generated",
)


class SEOMixin(models.Model):
    """Search-engine and social-sharing metadata for a public content object."""

    class RobotsDirective(models.TextChoices):
        INDEX_FOLLOW = "index,follow", "Index and follow links"
        INDEX_NOFOLLOW = "index,nofollow", "Index but do not follow links"
        NOINDEX_FOLLOW = "noindex,follow", "Do not index but follow links"
        NOINDEX_NOFOLLOW = "noindex,nofollow", "Do not index or follow links"

    meta_title = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Browser tab / search result title. Auto-generated when blank.",
    )
    meta_description = models.TextField(
        blank=True, default="",
        help_text=f"Search result snippet, ideally under {META_DESCRIPTION_LIMIT} characters. Auto-generated when blank.",
    )
    keywords = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Comma separated keywords. Auto-generated when blank.",
    )
    canonical_url = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Canonical path or absolute URL. Auto-generated when blank.",
    )
    robots = models.CharField(
        max_length=32, choices=RobotsDirective.choices, default=RobotsDirective.INDEX_FOLLOW,
        help_text="How search engines should treat this page.",
    )
    author = models.CharField(max_length=255, blank=True, default="")

    # --- Open Graph (Facebook, LinkedIn, WhatsApp previews) ----------------
    og_title = models.CharField(max_length=255, blank=True, default="")
    og_description = models.TextField(blank=True, default="")
    og_image = models.CharField(max_length=500, blank=True, default="", help_text="Absolute URL of the share image.")

    # --- Twitter / X cards -------------------------------------------------
    twitter_card = models.CharField(max_length=32, default="summary_large_image")
    twitter_title = models.CharField(max_length=255, blank=True, default="")
    twitter_description = models.TextField(blank=True, default="")
    twitter_image = models.CharField(max_length=500, blank=True, default="")

    # --- structured data ---------------------------------------------------
    schema_json = models.JSONField(
        blank=True, null=True,
        help_text="schema.org JSON-LD. Auto-generated when blank.",
    )

    # Bookkeeping: field name -> the value this mixin generated for it. Hidden
    # from the admin; it exists so editor overrides are never clobbered.
    seo_generated = models.JSONField(default=dict, editable=False, blank=True)

    class Meta:
        abstract = True

    # ------------------------------------------------------------------
    # Hooks - concrete models override these to describe themselves.
    # ------------------------------------------------------------------

    def seo_headline(self) -> str:
        """Human-readable name of this object (falls back to ``str()``)."""
        return strip_html(str(self))

    def seo_summary(self) -> str:
        """Plain-text body used to derive descriptions."""
        return ""

    def seo_image_url(self) -> str:
        """Absolute or root-relative URL of the primary image, if any."""
        return ""

    def seo_path(self) -> str:
        """Root-relative canonical path, e.g. ``/events/orientation-2026/``."""
        return "/"

    def seo_keyword_sources(self) -> list[str]:
        """Phrases the keyword list is built from."""
        return []

    def seo_schema_type(self) -> str:
        """schema.org ``@type`` for this object."""
        return "WebPage"

    def seo_schema_extra(self) -> dict:
        """Additional schema.org properties merged into the generated JSON-LD."""
        return {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def absolute_url(self, path_or_url: str) -> str:
        """Expand a root-relative path into an absolute URL using SITE_BASE_URL."""
        if not path_or_url:
            return ""
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url
        base = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
        return f"{base}{path_or_url if path_or_url.startswith('/') else '/' + path_or_url}"

    def _is_editor_supplied(self, field: str) -> bool:
        """True when the stored value did not come from this mixin."""
        current = getattr(self, field)
        if not current:
            return False
        generated = (self.seo_generated or {}).get(field)
        return current != generated

    def _autofill(self, field: str, compute, normalise=None) -> None:
        """
        Set ``field`` from ``compute()`` unless the editor supplied a value.

        When the editor did supply one, ``normalise`` (if given) tidies it -
        stripping HTML, clamping length - without replacing their wording.
        """
        if self._is_editor_supplied(field):
            if normalise is not None:
                setattr(self, field, normalise(getattr(self, field)))
            return

        value = compute()
        setattr(self, field, value)
        if self.seo_generated is None:
            self.seo_generated = {}
        self.seo_generated[field] = value

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate_seo_data(self) -> None:
        """
        Fill every auto-managed SEO field and normalise editor-supplied ones.

        Called from ``ContentBase.save()``, so editors get complete metadata
        without ever opening the SEO tab.
        """
        site_name = getattr(settings, "SITE_NAME", "")
        headline = self.seo_headline() or "Untitled"
        summary = self.seo_summary()

        def build_meta_title():
            suffix = f" | {site_name}" if site_name else ""
            # Guard the headline budget: a long site name must not squeeze the
            # actual page name down to nothing.
            budget = max(30, META_TITLE_LIMIT - len(suffix))
            return f"{summarise(headline, budget)}{suffix}"

        def build_meta_description():
            fallback = f"{headline} at {site_name}" if site_name else headline
            return summarise(summary or fallback, META_DESCRIPTION_LIMIT)

        self._autofill(
            "meta_title", build_meta_title,
            normalise=lambda value: clean_whitespace(strip_html(value)),
        )
        self._autofill(
            "meta_description", build_meta_description,
            normalise=lambda value: summarise(value, META_DESCRIPTION_LIMIT),
        )
        self._autofill(
            "canonical_url", self.seo_path,
            normalise=lambda value: value if value.startswith(("http://", "https://", "/")) else f"/{value}",
        )

        if not self.author and site_name:
            self.author = site_name

        # --- Open Graph ---------------------------------------------------
        self._autofill(
            "og_title", lambda: summarise(headline, META_TITLE_LIMIT),
            normalise=lambda value: clean_whitespace(strip_html(value)),
        )
        self._autofill(
            "og_description", lambda: summarise(self.meta_description, OG_DESCRIPTION_LIMIT),
            normalise=lambda value: summarise(value, OG_DESCRIPTION_LIMIT),
        )
        self._autofill("og_image", lambda: self.absolute_url(self.seo_image_url()))

        # --- Twitter ------------------------------------------------------
        self._autofill(
            "twitter_title", lambda: self.og_title,
            normalise=lambda value: clean_whitespace(strip_html(value)),
        )
        self._autofill(
            "twitter_description", lambda: summarise(self.og_description, OG_DESCRIPTION_LIMIT),
            normalise=lambda value: summarise(value, OG_DESCRIPTION_LIMIT),
        )
        self._autofill("twitter_image", lambda: self.og_image)
        if not self.twitter_card:
            self.twitter_card = "summary_large_image"

        # --- relation-dependent fields ------------------------------------
        # On a brand new row the many-to-many tables are still empty, so these
        # are refreshed again by sync_related_seo() once relations are written.
        self._autofill(
            "keywords", self._build_keywords,
            normalise=lambda value: clean_whitespace(strip_html(value)),
        )
        self._autofill("schema_json", self._build_schema)

    def sync_related_seo(self) -> None:
        """
        Recompute the SEO values that depend on many-to-many relations.

        Departments and categories are written after the object itself, so
        without this the keyword list and schema.org affiliations would only
        ever reflect an object's very first (relation-less) save. The admin
        calls this from ``save_related`` and the API serializers call it after
        assigning relations.

        Editor-supplied keywords and schema are left untouched, and the write
        is skipped entirely when nothing changed.
        """
        if not self.pk:
            return

        previous = {field: getattr(self, field) for field in RELATION_DEPENDENT_FIELDS}

        self._autofill("keywords", self._build_keywords)
        self._autofill("schema_json", self._build_schema)

        changed = [field for field in RELATION_DEPENDENT_FIELDS if getattr(self, field) != previous[field]]
        if changed:
            # `update_fields` keeps this to a targeted UPDATE and avoids
            # re-entering the full save() path.
            super().save(update_fields=[*changed, "seo_generated", "updated_at"])

    def _build_keywords(self, limit: int = 12) -> str:
        """De-duplicated, order-preserving keyword list from the model's hooks."""
        keywords: list[str] = []
        seen: set[str] = set()
        for source in self.seo_keyword_sources():
            for phrase in strip_html(source).split(","):
                phrase = clean_whitespace(phrase).lower()
                if len(phrase) < 3 or phrase in seen:
                    continue
                seen.add(phrase)
                keywords.append(phrase)
                if len(keywords) >= limit:
                    return ", ".join(keywords)
        return ", ".join(keywords)

    def _build_schema(self) -> dict:
        """schema.org JSON-LD describing this object."""
        site_name = getattr(settings, "SITE_NAME", "")
        schema = {
            "@context": "https://schema.org",
            "@type": self.seo_schema_type(),
            "name": self.seo_headline(),
            "description": self.meta_description,
            "url": self.absolute_url(self.canonical_url),
        }

        image = self.absolute_url(self.seo_image_url())
        if image:
            schema["image"] = image
        if site_name:
            schema["publisher"] = {"@type": "EducationalOrganization", "name": site_name}

        schema.update(self.seo_schema_extra())
        # Drop empty values so the rendered JSON-LD stays clean.
        return {key: value for key, value in schema.items() if value not in ("", None, [], {})}

    @property
    def schema_json_ld(self) -> str:
        """The schema as a string ready to drop into a ``<script>`` tag."""
        if not self.schema_json:
            return ""
        return json.dumps(self.schema_json, ensure_ascii=False)
