# MBU Backend

Content backend for the Mohan Babu University website. It manages three kinds
of content — **events**, **blogs** and **faculty profiles** — and exposes them
three ways:

| Surface | For | Where |
| --- | --- | --- |
| Admin dashboard | Editors | `/admin/` |
| REST API | The public website | `/api/v1/` |
| MCP server | Claude | `python -m mcp_server` |

Every piece of content gets complete SEO metadata (meta tags, Open Graph,
Twitter cards, schema.org JSON-LD) generated automatically, and every editor
override is preserved.

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
#    ...paste the result into DJANGO_SECRET_KEY in .env

# 3. Create the database
python manage.py migrate

# 4. Create an admin login
python manage.py createsuperuser

# 5. (Optional) Load sample content to explore
python manage.py seed_content

# 6. Run
python manage.py runserver
```

Then open:

- <http://127.0.0.1:8000/admin/> — the editor dashboard
- <http://127.0.0.1:8000/api/docs/> — interactive API documentation
- <http://127.0.0.1:8000/api/v1/events/> — the API itself

## Connecting Claude

```bash
# Issue a token for the MCP server
python manage.py create_api_token --username mcp-bot --create-user
```

Put the token in `.env` as `MBU_API_TOKEN`, copy `mcp.example.json` into your
MCP client's config, and restart the client. Claude then has 33 tools for
creating and updating content. Full walkthrough: **[docs/mcp.md](docs/mcp.md)**.

## Project layout

```
mbu_backend/
├── apps/
│   ├── core/          Shared bases, SEO engine, departments, dashboard
│   ├── events/        Events and achievements
│   ├── blogs/         Articles
│   └── faculty/       Staff profiles
├── mbu_backend/       Project configuration (settings split by environment)
├── mcp_server/        MCP server exposing the API to Claude
├── docs/              Documentation
├── tests/             Test suite (mirrors the source layout)
├── templates/         Admin template overrides
└── media/             Uploaded files
```

Each app follows the same shape: `models/`, `admin.py`, `api/` (serializers,
filters, views, urls) and `migrations/`.

## Common commands

```bash
python manage.py runserver                 # Development server
python manage.py test tests                # Run the test suite (95 tests)
python manage.py makemigrations            # After changing a model
python manage.py migrate                   # Apply migrations
python manage.py seed_content              # Load sample content
python manage.py seed_content --flush      # Reload it from scratch
python manage.py create_api_token --username mcp-bot --create-user
python manage.py collectstatic             # Before deploying
python -m mcp_server                       # Run the MCP server manually
```

## Documentation

Start at **[docs/README.md](docs/README.md)**, which links to:

- [Architecture](docs/architecture.md) — how the pieces fit together
- [Data model](docs/data-model.md) — every model and field
- [API reference](docs/api.md) — endpoints, filters, authentication
- [Admin guide](docs/admin-guide.md) — for content editors
- [MCP integration](docs/mcp.md) — connecting and using Claude
- [Deployment](docs/deployment.md) — running in production

## Tech stack

Django 5.2 · Django REST Framework · django-unfold (admin UI) · CKEditor ·
drf-spectacular (OpenAPI) · MCP Python SDK · SQLite in development,
PostgreSQL in production.
