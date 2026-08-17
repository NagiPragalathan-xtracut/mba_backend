# Data model

Every model, field and relationship.

## Overview

```
Department ──┬──< Event >──── EventCategory
             ├──< Blog  >──── BlogCategory (many-to-many)
             └──< Faculty >── Designation

Event    ──< EventImage      (one is_featured per event)
Blog     ──< BlogImage       (cover lives on Blog itself)
Faculty  ──< FacultySection  (repeatable heading + rich text)
         ──< FacultyBanner
```

`──<` is one-to-many, `>────` is many-to-one, `Department ──<` relations are
many-to-many.

## Fields shared by every model

From `TimeStampedModel`:

| Field | Type | Notes |
| --- | --- | --- |
| `unique_id` | UUID | Stable external identifier. Prefer this over `id` in other systems. |
| `created_at` | datetime | Set once, indexed. |
| `updated_at` | datetime | Refreshed on every save. |

From `ContentBase` (Event, Blog, Faculty):

| Field | Type | Notes |
| --- | --- | --- |
| `slug` | slug | Unique. Generated from the title/name; duplicates get `-1`, `-2`… |
| `is_published` | bool | Unpublished rows are invisible to anonymous API callers. |
| `is_featured` | bool | Highlight on listing pages. |
| `display_order` | int | Lower first; ties fall back to newest-first. |

Plus the full SEO set — see [SEO fields](#seo-fields) below.

---

## Taxonomies

All four share the `NamedTaxonomy` shape: `name` (unique), `slug` (auto),
`description`, `display_order`, `is_active`.

### Department

Shared by all three content types, so a department is spelled one way
everywhere and the website can filter any content by the same slug.

| Field | Type | Notes |
| --- | --- | --- |
| `short_name` | char(32) | Abbreviation for compact UI, e.g. `CSE`. |

`department.label` returns the short name when set, otherwise the full name.

### EventCategory

How an event is classified. The project ships with **Upcoming** and
**Achievements**, created by a data migration
(`apps/events/migrations/0002_default_categories.py`) so the first event can be
created immediately. More can be added at any time.

### BlogCategory

Topic buckets for articles — Research, Campus Life, Placements. Separate from
event categories on purpose: the two lists are free to diverge.

### Designation

Faculty job titles. `display_order` is useful for seniority ordering.

---

## Event

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | char(255) | ✅ | Event name. |
| `slug` | slug | auto | From the title. |
| `category` | FK → EventCategory | ✅ | `PROTECT` — a category in use cannot be deleted. |
| `departments` | M2M → Department | | Empty means university-wide. |
| `summary` | text | | Listing teaser. Derived from `content` when blank. |
| `content` | rich text | ✅ | CKEditor body with image upload. |
| `event_date` | date | | Start date. |
| `end_date` | date | | For multi-day events. Must not precede `event_date`. |
| `venue` | char(255) | | |

**Featured image.** Not a column: it is whichever `EventImage` carries
`is_featured`. `event.featured_image` returns that row (falling back to the
first photo), `event.featured_image_url` its URL.

**Ordering:** `display_order`, then `-event_date`, then `-created_at`.

### EventImage

| Field | Type | Notes |
| --- | --- | --- |
| `event` | FK → Event | Cascade delete. |
| `image` | SVGImageField | Stored under `media/events/gallery/`. |
| `alt` | char(255) | Falls back to the caption, then the event title. |
| `caption` | char(500) | |
| `is_featured` | bool | At most one per event, enforced by a database constraint. |
| `display_order` | int | |

Behaviour on save:

1. The first photo uploaded for an event becomes featured automatically.
2. Setting `is_featured=True` demotes the previous one, inside a transaction.
3. A partial unique constraint (`unique_featured_image_per_event`) guarantees
   the invariant even for writes that bypass the model.

---

## Blog

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | char(255) | ✅ | |
| `slug` | slug | auto | |
| `categories` | M2M → BlogCategory | | |
| `departments` | M2M → Department | | Empty means university-wide. |
| `summary` | text | | Derived from `content` when blank. |
| `content` | rich text | ✅ | |
| `featured_image` | SVGImageField | | Cover image, uploaded directly. |
| `featured_image_alt` | char(255) | | Defaults to the title. |
| `published_date` | date | | Defaults to today. Indexed. |
| `author_name` | char(255) | | Byline. |

`blog.reading_time_minutes` estimates read time at 200 words per minute,
minimum one.

**Ordering:** `display_order`, then `-published_date`, then `-created_at`.

### BlogImage

In-article photos: `blog`, `image`, `alt`, `caption`, `display_order`. Same alt
fallback behaviour as `EventImage`, but no featured flag — that is what
`Blog.featured_image` is for.

---

## Faculty

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `name` | char(255) | ✅ | The slug is generated from this, not a `title`. |
| `slug` | slug | auto | |
| `image` | SVGImageField | | Profile photo, `media/faculty/photos/`. |
| `image_alt` | char(255) | | Defaults to the name. |
| `designation` | FK → Designation | ✅ | `PROTECT`. |
| `departments` | M2M → Department | | A person may belong to several. |
| `qualification` | char(500) | | e.g. `Ph.D., M.Tech, B.Tech`. |
| `mail_id` | email | | Optional, shown publicly when filled. |
| `phone_number` | char(20) | | Optional. Validated against `[0-9+()\- ]{6,20}`. |
| `profile_link` | URL | | Personal site, Google Scholar, ORCID. |

**Ordering:** `display_order`, then `name`.

### FacultySection

The repeatable "heading + rich text" block — the "+" button in the admin.

| Field | Type | Notes |
| --- | --- | --- |
| `faculty` | FK → Faculty | Cascade delete. |
| `heading` | char(255) | Unique per profile. |
| `content` | rich text | Uses the compact CKEditor toolbar. |
| `display_order` | int | Controls the order on the profile page. |
| `is_visible` | bool | Hide without deleting. |

Typical headings: Biography, Publications, Awards, Workshops, Work Experience,
Projects, Patents. Nothing is hard-coded — add whatever a profile needs.

The first visible section also feeds the auto-generated SEO description.

### FacultyBanner

Wide header images: `faculty`, `image`, `alt`, `display_order`.

---

## SEO fields

Present on Event, Blog and Faculty. **Leave them blank** — they generate
themselves and stay in sync. Fill one in and it is preserved verbatim.

| Field | Generated from |
| --- | --- |
| `meta_title` | Headline + site name, clamped to ~70 characters |
| `meta_description` | Summary or content, plain text, ≤160 characters |
| `keywords` | Title, category, departments, qualification |
| `canonical_url` | `/events/<slug>/`, `/blogs/<slug>/`, `/faculty/<slug>/` |
| `robots` | Defaults to `index,follow` |
| `author` | Site name |
| `og_title`, `og_description`, `og_image` | Headline, description, primary image |
| `twitter_card`, `twitter_title`, `twitter_description`, `twitter_image` | Falls back to the Open Graph values |
| `schema_json` | JSON-LD: `Event`, `BlogPosting` or `Person` |

`schema_json_ld` renders the schema as a string ready for a `<script>` tag.

`seo_generated` is an internal, non-editable map recording which values the
system produced. It is what lets a regeneration tell "ours" from "the editor's".

### Generated schema.org types

| Model | `@type` | Extra properties |
| --- | --- | --- |
| Event | `Event` | `startDate`, `endDate`, `location` |
| Blog | `BlogPosting` | `datePublished`, `dateModified`, `author` |
| Faculty | `Person` | `jobTitle`, `email`, `telephone`, `sameAs`, `affiliation` |

---

## Deletion behaviour

| Relationship | On delete |
| --- | --- |
| Event → EventCategory | `PROTECT` — the category cannot be deleted while used |
| Faculty → Designation | `PROTECT` |
| EventImage → Event | `CASCADE` |
| BlogImage → Blog | `CASCADE` |
| FacultySection / FacultyBanner → Faculty | `CASCADE` |
| Any content → Department (M2M) | Removing a department just unlinks it |

Prefer unpublishing over deleting: `is_published=False` hides content from the
website while keeping it and its images recoverable.
