# MBU Backend Documentation

Start here. Each page below covers one area; follow the one that matches what
you are trying to do.

## By role

**I edit content on the website**
→ [Admin guide](admin-guide.md) — creating events, blogs and faculty profiles,
managing photos, and what the SEO tab does.

**I build the website frontend**
→ [API reference](api.md) — endpoints, filters, pagination, and the exact shape
of every response.

**I want Claude to manage content**
→ [MCP integration](mcp.md) — connecting Claude, the available tools, and
example prompts.

**I work on this codebase**
→ [Architecture](architecture.md) then [Data model](data-model.md).

**I deploy this**
→ [Deployment](deployment.md).

## All pages

| Page | Covers |
| --- | --- |
| [Architecture](architecture.md) | Project layout, the SEO engine, request flow, design decisions |
| [Data model](data-model.md) | Every model, field and relationship |
| [API reference](api.md) | REST endpoints, the common feed, authentication, filtering, pagination |
| [Admin guide](admin-guide.md) | Day-to-day content editing |
| [MCP integration](mcp.md) | Claude setup, all 33 tools, worked examples |
| [Deployment](deployment.md) | Production settings, S3 media storage, checklist, web server setup |

## Conventions used throughout

- **Slugs identify things.** Departments, categories and designations are
  referenced by slug (`computer-science-engineering`) rather than numeric id,
  in the API and in the MCP tools alike.
- **Detail routes are flexible.** `/api/v1/events/<x>/` accepts a slug, a
  numeric id or a UUID.
- **Reads are public, writes need a token.** Anonymous callers also never see
  unpublished content.
- **Events and blogs publish together.** They are separate tables, but
  `/api/v1/news-events/` serves both in one normalised, UI-ready shape so a
  frontend renders them with one set of components.
- **SEO is generated, not typed.** Leave the SEO fields blank and they fill
  themselves; fill one in and it is never overwritten.

## Keeping these docs current

Documentation changes ship in the same commit as the code they describe:

- New feature → document it here
- Changed behaviour → update the affected page
- Removed functionality → delete it from the docs

High-level changes go in the root [README](../README.md); detailed explanations
belong on the page above that owns that area.
