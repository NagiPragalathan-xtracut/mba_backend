# Architecture

How the project is put together and why.

## The three surfaces

One database, three ways in:

```
                    ┌─────────────────┐
   Editors ────────▶│  Admin (Unfold) │──┐
                    └─────────────────┘  │
                                         ▼
                    ┌─────────────────┐  ┌──────────┐   ┌──────────┐
   Website  ───────▶│   REST API      │─▶│  Models  │──▶│    DB    │
                    └─────────────────┘  └──────────┘   └──────────┘
                             ▲             ▲
                    ┌─────────────────┐    │
   Claude   ───────▶│   MCP server    │────┘ (over HTTP, via the API)
                    └─────────────────┘
```

The MCP server deliberately goes **through the REST API** rather than importing
Django directly. That means:

- every write passes the same validation the admin and the website use;
- the MCP server works against a local backend or a deployed one, unchanged;
- it can run on a different machine from Django.

## Directory layout

```
apps/
├── core/                   Shared foundations - no content of its own
│   ├── models/
│   │   ├── base.py         TimeStampedModel, OrderedModel, NamedTaxonomy
│   │   ├── seo.py          SEOMixin - the SEO engine
│   │   ├── content.py      ContentBase - slug + publishing + SEO
│   │   └── department.py   Department, shared by all three apps
│   ├── admin/
│   │   ├── mixins.py       Shared fieldsets, actions, image previews
│   │   ├── dashboard.py    The admin landing page
│   │   └── department.py
│   ├── api/
│   │   ├── serializers.py  SEO serializer, taxonomy base, slug relations
│   │   ├── viewsets.py     Visibility + flexible lookup mixins
│   │   ├── pagination.py
│   │   ├── views.py        Departments, health check
│   │   └── urls.py
│   ├── management/commands/
│   │   ├── create_api_token.py
│   │   └── seed_content.py
│   ├── fields.py           SVGImageField
│   └── utils/              strip_html, summarise, unique_slugify, iso_date
│
├── events/   ┐
├── blogs/    │ Same shape each: models/, admin.py, api/, migrations/
└── faculty/  ┘
```

Each content app depends on `core`; `core` depends on none of them (the
dashboard imports them lazily, inside functions, to avoid a circular import at
startup).

## The model hierarchy

```
models.Model
└── TimeStampedModel          unique_id (UUID), created_at, updated_at
    ├── OrderedModel          + display_order          → gallery images, sections
    ├── NamedTaxonomy         + name, slug, description, is_active
    │   └── Department, EventCategory, BlogCategory, Designation
    └── ContentBase           + slug, is_published, is_featured, display_order
        │                       and everything from SEOMixin
        └── Event, Blog, Faculty
```

`ContentBase.save()` is the single place where the ordering rules live: the
slug is generated first (the canonical URL is built from it), then SEO data,
then the row is written.

## The SEO engine

Every public content type needs the same ~15 tags. Rather than writing them
three times, `SEOMixin` (`apps/core/models/seo.py`) stores the fields and fills
the blanks from six small hooks each model implements:

| Hook | Answers |
| --- | --- |
| `seo_headline()` | What is this called? |
| `seo_summary()` | What is it about? |
| `seo_image_url()` | What image represents it? |
| `seo_path()` | Where does it live on the website? |
| `seo_keyword_sources()` | What phrases describe it? |
| `seo_schema_type()` / `seo_schema_extra()` | What is it, in schema.org terms? |

Adding a fourth content type means implementing those six hooks — not copying
another SEO block.

### Editor input is never overwritten

Each generated value is recorded in a hidden `seo_generated` map. On the next
save the mixin compares the stored value against what it generated last time:

- **still equal** → the value is ours, safe to refresh from the new content;
- **different** → an editor typed it, so leave the wording alone (only tidy
  stray HTML and clamp the length).

That distinction is what makes the next section possible.

### Relations arrive late

Django writes an object first and its many-to-many rows second. Keywords and
schema.org affiliations depend on departments and categories, so on the very
first save they would be computed against empty relations.

`sync_related_seo()` fixes that up afterwards, and all three write paths call it:

| Path | Where |
| --- | --- |
| Admin | `ContentAdminMixin.save_related()` |
| API | `SEOModelSerializerMixin.create()` / `.update()` |
| Management commands | Explicitly, after `.set()` |

It only issues an `UPDATE` when something actually changed.

### One more trap worth knowing

`Model.save(update_fields=[...])` writes *only* the listed columns — and
Django's own `update_or_create()` uses it. Values derived inside `save()` would
be computed and then silently dropped. `ContentBase.save()` therefore adds the
slug and every SEO column to any `update_fields` it is given. There is a
regression test for this
(`tests/apps/test_core_seo.py::test_update_fields_save_still_persists_generated_values`).

## Featured images: two different rules

The two content types genuinely differ, so they are modelled differently:

- **Events** — the highlight is *chosen from the uploaded gallery*
  (`EventImage.is_featured`). A partial unique constraint guarantees at most
  one per event at the database level, `EventImage.save()` demotes the previous
  winner inside a transaction, and the first photo uploaded is featured
  automatically so listing pages are never image-less.
- **Blogs** — the cover is uploaded directly onto the post
  (`Blog.featured_image`), because a post usually has one deliberate cover
  distinct from any in-article photos.

## Faculty profiles are not a fixed form

Departments describe staff differently — some want Publications and Patents,
others want Industry Experience. So a profile's long-form content lives in
`FacultySection` rows (heading + rich text + order) that an editor adds with the
"+" button, rather than a fixed set of columns. Only the structured, queryable
fields (name, designation, departments, qualification, contact) are columns.

## Settings

Split by environment under `mbu_backend/settings/`:

| Module | Purpose |
| --- | --- |
| `base.py` | Everything shared. Reads all configuration from the environment. |
| `development.py` | `DEBUG=True`, permissive hosts and CORS, console email. |
| `production.py` | HSTS, secure cookies, SSL redirect, JSON-only API. Fails at import if `DJANGO_SECRET_KEY` is missing. |

`manage.py`, `wsgi.py` and `asgi.py` pick the module from `DJANGO_ENV`
(default `development`). No secret has a working default in production — an
insecure boot is impossible.

## Custom fields

`SVGImageField` (`apps/core/fields.py`) behaves like `ImageField` but also
accepts SVG. Django validates images through Pillow, which cannot open SVG, so
logos and icons would otherwise be rejected. The field keeps the Pillow check
for raster formats and falls back to an XML check whose root element must be
`<svg>` — detected from the *content*, so a renamed file cannot smuggle
arbitrary markup through.

## Rich text editing

Long-form content (`Event.content`, `Blog.content`, `FacultySection.content`)
uses CKEditor through `django-ckeditor`, with two toolbars configured in
`settings/base.py`: `default` (full) and `compact` (faculty sections).

Two configuration details are deliberate:

- `filebrowserUploadMethod: "form"` — the CSRF-safe upload path
  `django-ckeditor` recommends. The trade-off is that pasting an image
  straight into the editor does not auto-upload; the image dialog's upload tab
  does. CKEditor logs a `clipboard-image-handling-disabled` notice about this.
- `versionCheck: False` — CKEditor 4 otherwise renders a red "this version is
  not secure" banner **inside the editor body**, where content editors see it.
  The notice is aimed at developers, so it is turned off in the UI.

### Known limitation: CKEditor 4 is end-of-life

`django-ckeditor` 6.7.0 bundles CKEditor 4.22.1. CKEditor 4 reached end of
life in 2023 and further security patches are only available under a
commercial LTS licence. Turning off `versionCheck` hides the banner; it does
not change that fact.

Current exposure is limited — the editor is only reachable by authenticated
staff behind `/admin/`, and the upload endpoints are staff-gated (verified:
`/ckeditor/upload/` and `/ckeditor/browse/` both redirect to the login page).

If the editor needs to be replaced, the blast radius is small: three model
fields and the `CKEDITOR_CONFIGS` block. The realistic options are
`django-ckeditor-5` (CKEditor 5, actively maintained, GPL or commercial) or
`django-tinymce`. Rich text is stored as HTML in a plain text column, so no
data migration is required.

## API design

- **Slug-addressed relations.** `{"departments": ["cse", "ece"]}` rather than
  `[3, 7]`, with an error message that names the offending slug.
- **Flexible detail lookup.** Slug, numeric id or UUID all resolve.
- **Visibility by caller.** Anonymous requests see only published rows;
  authenticated ones see drafts too.
- **Two serializers per model.** A light one for lists (no rich-text body, no
  gallery) and a full one for detail.
- **Nested `seo` object.** All SEO fields in one place so a frontend can render
  every meta tag from a single object.

## Testing

95 tests in `tests/`, mirroring the source layout:

| File | Covers |
| --- | --- |
| `test_core_utils.py` | HTML stripping, summarising, slug uniqueness |
| `test_core_seo.py` | Generation, editor overrides, relation sync, `update_fields` |
| `test_events.py` | Slugs, summaries, the featured-image rules and constraint |
| `test_blogs.py` | Dates, reading time, categories, schema |
| `test_faculty.py` | Multi-department, sections, uniqueness, validation |
| `test_api.py` | Permissions, slug relations, filters, uploads, pagination |
| `test_mcp_server.py` | Tool registration, argument shaping, error messages |

```bash
python manage.py test tests
```
