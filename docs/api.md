# API reference

Base URL: `/api/v1/`

Interactive documentation is generated from the code and always current:

| URL | What |
| --- | --- |
| `/api/docs/` | Swagger UI — try requests in the browser |
| `/api/redoc/` | ReDoc — easier to read |
| `/api/schema/` | Raw OpenAPI 3 schema |

## Authentication

Reads are public. Writes require a token.

```bash
python manage.py create_api_token --username mcp-bot --create-user
```

```http
Authorization: Token fb52d1b72abaa2355ca21d985e170d6bff0c5ede
```

Rotate a compromised token with `--rotate`; the old key stops working
immediately.

| Caller | Can read published | Can read drafts | Can write |
| --- | --- | --- | --- |
| Anonymous | ✅ | ❌ | ❌ |
| Token / session | ✅ | ✅ | ✅ |

## Identifying a resource

Detail routes accept **a slug, a numeric id or a UUID**, interchangeably:

```
GET /api/v1/events/national-tech-symposium-2026/
GET /api/v1/events/12/
GET /api/v1/events/3f2a91c4-...-e7b3/
```

Relations are written **by slug**:

```json
{ "category": "upcoming", "departments": ["cse", "school-of-management"] }
```

An unknown slug returns a message naming it:

```json
{ "category": ["No Event Category exists with slug 'nope'. Create it first, or pass one of the existing slugs."] }
```

## Pagination

Every list response:

```json
{
  "count": 42,
  "total_pages": 3,
  "current_page": 1,
  "page_size": 20,
  "next": "http://.../api/v1/events/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

Control it with `?page=2&page_size=50` (maximum 100).

## Endpoints

### The common feed

Events and blog posts live in separate tables but the website shows them on one
page, so these three routes serve both through a single, UI-ready shape. Every
value is pre-formatted server-side — dates are already `"18 Dec"`, bodies are
already split into paragraphs — so a frontend renders them without transforming
anything.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/news-events/` | Merged, filterable, paginated feed of events + blogs |
| `GET` | `/news-events/{slug}/` | One entry, from whichever table holds it |
| `GET` | `/news-events/categories/` | Category filter options, de-duplicated across both |
| `GET` | `/news-events/courses/` | Course filter options, counted across both |

Read-only and public. Writes go through `/events/` and `/blogs/`, which is where
validation and permissions live.

### Content

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/events/` | List events |
| `POST` | `/events/` | Create an event |
| `GET` | `/events/{id}/` | Retrieve one event with its gallery |
| `PATCH` | `/events/{id}/` | Update an event |
| `DELETE` | `/events/{id}/` | Delete an event and its photos |
| `POST` | `/events/{id}/images/` | Upload a gallery photo (multipart) |
| `GET/POST` | `/blogs/` | List / create blog posts |
| `GET/PATCH/DELETE` | `/blogs/{id}/` | Retrieve, update, delete |
| `POST` | `/blogs/{id}/images/` | Upload an in-article photo (multipart) |
| `GET/POST` | `/faculty/` | List / create faculty profiles |
| `GET/PATCH/DELETE` | `/faculty/{id}/` | Retrieve, update, delete |
| `POST` | `/faculty/{id}/sections/` | Add a profile section |
| `POST` | `/faculty/{id}/banners/` | Upload a banner (multipart) |

### Taxonomies

`GET`/`POST` on the collection, `GET`/`PATCH`/`DELETE` on `{slug}`:

`/departments/` · `/courses/` · `/event-categories/` · `/blog-categories/` ·
`/designations/`

### Sub-resources

Direct CRUD when you already know the row id:

`/event-images/` · `/blog-images/` · `/faculty-sections/` · `/faculty-banners/`

`POST /event-images/{id}/set-featured/` promotes an existing gallery photo to
the event's highlight image.

### Health

`GET /api/v1/health/` — reports API and database availability, and whether the
request was authenticated. Never cached; safe to poll.

```json
{ "status": "healthy", "database": "connected", "authenticated": true, "user": "mcp-bot" }
```

## Filtering

Shared by every list endpoint: `?search=`, `?ordering=`, `?page=`, `?page_size=`.

### The common feed

| Parameter | Example | Notes |
| --- | --- | --- |
| `type` | `?type=event` | `event` or `blog`; omit for both. Anything else is a 400. |
| `category` | `?category=announcements` | Slug. `all` is treated as no filter. |
| `course` | `?course=mba-finance` | Slug. `all` is treated as no filter. |
| `department` | `?department=school-of-management` | Slug. |
| `search` | `?search=conclave` | Case-insensitive title match. |
| `featured` | `?featured=true` | Entries flagged as featured. |
| `date_from` / `date_to` | `?date_from=2024-12-01` | Applies to `event_date` and `published_date`. |

Filters that only one model can express are skipped for the other rather than
erroring, so `?category=leadership` narrows the posts and simply matches no
events.

### Events

| Parameter | Example |
| --- | --- |
| `category` | `?category=achievements` |
| `department` | `?department=computer-science-engineering` |
| `course` | `?course=mba-finance` |
| `is_featured` / `is_published` | `?is_featured=true` |
| `date_from` / `date_to` | `?date_from=2026-01-01&date_to=2026-12-31` |
| `year` | `?year=2026` |
| `ordering` | `?ordering=-event_date` |

### Blogs

`category`, `department`, `course`, `author`, `is_featured`, `is_published`,
`date_from`, `date_to`, `year`, `ordering` (`display_order`,
`published_date`, `created_at`, `title`).

### Faculty

`department`, `designation`, `qualification` (partial match), `has_email`,
`is_featured`, `is_published`, `ordering` (`display_order`, `name`,
`created_at`).

## Response shapes

### Event list entry

```json
{
  "id": 1,
  "unique_id": "3f2a91c4-...",
  "title": "National Tech Symposium 2026",
  "slug": "national-tech-symposium-2026",
  "summary": "A two-day symposium on applied AI and robotics.",
  "category": "upcoming",
  "category_name": "Upcoming",
  "departments": ["computer-science-engineering"],
  "event_date": "2026-10-01",
  "end_date": "2026-10-02",
  "venue": "Main Auditorium",
  "featured_image_url": "http://.../media/events/gallery/stage.png",
  "is_published": true,
  "is_featured": false,
  "display_order": 10,
  "created_at": "2026-08-17T12:00:00Z",
  "updated_at": "2026-08-17T12:00:00Z"
}
```

The detail response adds `content`, `category_detail`, `departments_detail`,
`images[]`, every SEO field, and a nested `seo` object.

### Feed entry

The same shape whether the row is an event or a blog post. `type` is the
discriminator; the fields a given kind cannot fill come back empty rather than
absent, so a client never has to branch.

```json
{
  "id": 1,
  "type": "event",
  "slug": "srm-drug-awareness-programme",
  "title": "Drug Awareness Programme",
  "excerpt": "The Department of Biotechnology, with the NSS, held a session …",
  "image": "http://127.0.0.1:8000/media/events/gallery/poster.jpg",
  "category": "Events",
  "category_slug": "events",
  "date": "18 Dec",
  "date_long": "18 Dec 2024",
  "date_label": "18.12.2024",
  "date_iso": "2024-12-18",
  "timing": "10:00 AM – 11:00 AM",
  "venue": "Seminar Hall",
  "author": "Mohan Babu University",
  "reading_time_minutes": 0,
  "paragraphs": ["The Department of Biotechnology …", "Expert speakers …"],
  "content_html": "<p>The Department of Biotechnology …</p>",
  "gallery": [{ "image": "…", "alt": "…", "caption": "" }],
  "departments": ["School of Management"],
  "courses": ["MBA"],
  "course_slugs": ["mba"],
  "href": "/news-events/srm-drug-awareness-programme",
  "is_featured": false,
  "display_order": 10,
  "seo": { "…": "see below" }
}
```

`timing` is empty for anything without a start time — news and announcements —
and `reading_time_minutes` is `0` for events. Blog entries carry a
`reading_time_minutes` and an empty `timing` / `venue` instead.

### The nested `seo` object

Present on every content detail response, so a frontend can render all the meta
tags from one place:

```json
{
  "seo": {
    "meta_title": "National Tech Symposium 2026 | Mohan Babu University",
    "meta_description": "A two-day symposium on applied AI and robotics.",
    "keywords": "national tech symposium 2026, upcoming, computer science & engineering",
    "canonical_url": "/events/national-tech-symposium-2026/",
    "robots": "index,follow",
    "author": "Mohan Babu University",
    "og_title": "National Tech Symposium 2026",
    "og_description": "A two-day symposium on applied AI and robotics.",
    "og_image": "https://.../media/events/gallery/stage.png",
    "twitter_card": "summary_large_image",
    "twitter_title": "National Tech Symposium 2026",
    "twitter_description": "A two-day symposium on applied AI and robotics.",
    "twitter_image": "https://.../media/events/gallery/stage.png",
    "schema_json": { "@context": "https://schema.org", "@type": "Event", "...": "..." }
  }
}
```

### Faculty detail

Adds `sections[]` (heading, content, display_order, is_visible) in display
order, plus `banners[]` and `designation_detail`.

## Worked examples

### Create an event and give it a highlight photo

```bash
TOKEN=fb52d1b7...

curl -X POST http://127.0.0.1:8000/api/v1/events/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{
        "title": "National Tech Symposium 2026",
        "category": "upcoming",
        "departments": ["computer-science-engineering"],
        "content": "<p>Two days of talks on applied AI and robotics.</p>",
        "event_date": "2026-10-01",
        "end_date": "2026-10-02",
        "venue": "Main Auditorium"
      }'

curl -X POST http://127.0.0.1:8000/api/v1/events/national-tech-symposium-2026/images/ \
  -H "Authorization: Token $TOKEN" \
  -F "image=@/path/to/stage.jpg" -F "alt=Main stage" -F "is_featured=true"
```

### Build a faculty profile

```bash
curl -X POST http://127.0.0.1:8000/api/v1/faculty/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{
        "name": "Dr. Anitha Rao",
        "designation": "professor",
        "departments": ["computer-science-engineering"],
        "qualification": "Ph.D., M.Tech, B.Tech",
        "mail_id": "anitha.rao@example.edu"
      }'

curl -X POST http://127.0.0.1:8000/api/v1/faculty/dr-anitha-rao/sections/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"heading": "Publications", "content": "<ul><li>Paper A</li></ul>", "display_order": 20}'

curl -X PATCH http://127.0.0.1:8000/api/v1/faculty/dr-anitha-rao/ \
  -H "Authorization: Token $TOKEN" -F "image=@/path/to/portrait.jpg"
```

### Unpublish rather than delete

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/events/old-event/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"is_published": false}'
```

## Errors

| Status | Meaning | Typical fix |
| --- | --- | --- |
| `400` | Validation failed | Read the per-field messages in the body |
| `401` | No or invalid token | Set `Authorization: Token <key>` |
| `403` | Authenticated but not allowed | Check the token's user |
| `404` | No such object | Check the slug / id |
| `405` | Wrong method | e.g. `PATCH`, not `POST`, to update |

Validation errors are keyed by field:

```json
{ "end_date": ["End date cannot be earlier than the event date."] }
```

## CORS

Frontend origins are allowed via `CORS_ALLOWED_ORIGINS` in `.env`:

```
CORS_ALLOWED_ORIGINS=https://www.example.edu,https://staging.example.edu
```

`CORS_ALLOW_ALL_ORIGINS=True` is the development default and must stay off in
production.
