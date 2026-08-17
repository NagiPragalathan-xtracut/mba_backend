# MCP integration — managing content with Claude

The MCP server lets Claude create and update events, blog posts and faculty
profiles by talking to this backend. It runs as a separate process, connects to
the REST API with a token, and exposes 33 tools.

Because every write goes through the API, Claude is subject to exactly the same
validation as the admin — it cannot create malformed content.

---

## Setup

### 1. Issue a token

```bash
python manage.py create_api_token --username mcp-bot --create-user
```

This creates a staff account with **no usable password** — it can only act
through its token, never log into the admin — and prints the key:

```
Token for 'mcp-bot': fb52d1b72abaa2355ca21d985e170d6bff0c5ede
```

Rotate it any time with `--rotate`; the old key stops working immediately.

### 2. Configure the server

Add the token to `.env`:

```dotenv
MBU_API_BASE_URL=http://127.0.0.1:8000
MBU_API_TOKEN=fb52d1b72abaa2355ca21d985e170d6bff0c5ede
MBU_API_TIMEOUT=60
```

### 3. Register it with your MCP client

Copy `mcp.example.json` into your client's config and fix the `cwd` path:

```json
{
  "mcpServers": {
    "mbu-backend": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\Users\\Admin\\Documents\\Work\\mbu_backend",
      "env": {
        "MBU_API_BASE_URL": "http://127.0.0.1:8000",
        "MBU_API_TOKEN": "fb52d1b7..."
      }
    }
  }
}
```

| Client | Config file |
| --- | --- |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code | `.mcp.json` in the project root, or `claude mcp add` |

Values in the `env` block override `.env`, so one checkout can serve one client
against local and another against production.

### 4. Restart the client and check

Make sure Django is running (`python manage.py runserver`), then ask Claude:

> Check the MBU backend is reachable.

It calls `check_backend` and should report:

```json
{ "backend": "http://127.0.0.1:8000", "status": "healthy",
  "database": "connected", "token_configured": true,
  "authenticated": true, "user": "mcp-bot" }
```

---

## What Claude knows

The server ships instructions Claude reads before choosing a tool:

1. Departments, categories and designations are referenced **by slug** — look
   them up first with the matching `list_*` tool.
2. Create the event, blog or profile **before** uploading its images.
3. Image paths must be absolute paths on the machine running the MCP server.
4. Never write SEO fields — they generate themselves.
5. Prefer unpublishing over deleting.
6. If something fails, run `check_backend` to tell a stopped server from a bad
   token from invalid data.

---

## The tools

### Taxonomy & diagnostics (9)

| Tool | Does |
| --- | --- |
| `check_backend` | Verify connectivity and the token |
| `list_departments` | Departments and their slugs |
| `create_department` | Add a department |
| `list_event_categories` | Event categories (Upcoming, Achievements, …) |
| `create_event_category` | Add an event category |
| `list_blog_categories` | Blog categories |
| `create_blog_category` | Add a blog category |
| `list_designations` | Faculty job titles |
| `create_designation` | Add a designation |

### Events (7)

| Tool | Does |
| --- | --- |
| `list_events` | Filter by category, department, year or free text |
| `get_event` | One event in full, including its gallery |
| `create_event` | Create an event or achievement |
| `update_event` | Change only the fields you pass |
| `upload_event_image` | Add a gallery photo, optionally as the highlight |
| `set_event_featured_image` | Promote an already-uploaded photo |
| `delete_event` | Permanent delete |

### Blogs (7)

| Tool | Does |
| --- | --- |
| `list_blogs` | Filter by category, department, author, year or text |
| `get_blog` | One post in full |
| `create_blog` | Create a post |
| `update_blog` | Change only the fields you pass |
| `set_blog_cover_image` | Set the cover / social preview image |
| `upload_blog_image` | Add an in-article photo |
| `delete_blog` | Permanent delete |

### Faculty (10)

| Tool | Does |
| --- | --- |
| `list_faculty` | Filter by department, designation or text |
| `get_faculty` | One profile in full, including its sections |
| `create_faculty` | Create a profile |
| `update_faculty` | Change only the fields you pass |
| `add_faculty_section` | Add a "heading + body" block |
| `update_faculty_section` | Edit one section |
| `delete_faculty_section` | Remove one section |
| `set_faculty_photo` | Set the portrait |
| `upload_faculty_banner` | Add a wide header image |
| `delete_faculty` | Permanent delete |

---

## Conventions in the tool arguments

**Lists are comma-separated strings**, because that is what models produce most
reliably and it reads naturally:

```
departments: "computer-science-engineering, school-of-management"
```

**Content accepts plain text or HTML.** Plain prose is converted to HTML
paragraphs on blank lines; anything already containing markup is stored
untouched — so a bulleted list can be passed as `<ul><li>…</li></ul>`.

**Updates are partial.** Only the arguments actually passed are changed;
everything else keeps its value. Passing `departments` replaces the whole set.

**Identifiers are flexible.** `identifier` accepts a slug, numeric id or UUID.

---

## Example conversations

### Publishing an event with photos

> Add an upcoming event for the CSE and ECE departments: "National Tech
> Symposium 2026", 1–2 October 2026 in the Main Auditorium. It's a two-day
> symposium on applied AI, embedded systems and robotics. Use
> `C:\photos\symposium-stage.jpg` as the highlight image.

Claude will:

1. `list_departments` → confirm the CSE and ECE slugs
2. `list_event_categories` → confirm `upcoming`
3. `create_event` → with both departments and HTML content
4. `upload_event_image` → with `is_featured=true`

### Building a faculty profile

> Create a profile for Dr. Anitha Rao, Professor in Computer Science. Ph.D.,
> M.Tech, B.Tech. Email anitha.rao@example.edu. Add a Biography section about
> her distributed-systems research, a Publications section with her three 2025
> papers, and an Awards section for the 2024 Best Faculty Award.

Claude will `list_designations`, `list_departments`, `create_faculty`, then
call `add_faculty_section` three times with sensible display orders.

### Bulk tidying

> List every unpublished blog post from 2025 and tell me what they are.

> Unpublish the "Placement Season 2026" post — it needs rechecking.

> The Robotics Lab post should also be in the Research category.

### Auditing

> Which faculty profiles have no email address?

> Show me all achievements from 2026 that have no photos.

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| "Cannot reach the backend" | Django is not running | `python manage.py runserver` |
| "Authentication failed (401)" | Missing or wrong token | Re-run `create_api_token`, update `.env`, restart the client |
| "No Department exists with slug 'x'" | Guessed slug | Call `list_departments` first |
| "No file at '…'" | Relative or wrong path | Pass an absolute path |
| "not a supported image type" | Wrong extension | png, jpg, gif, webp, bmp, avif or svg |
| Tools missing in the client | Config not loaded | Check `cwd`, then fully restart the client |
| Writes fail, reads work | Token missing | The server logs a warning at startup — check its stderr |

Run the server by hand to see its logs:

```bash
python -m mcp_server
```

It logs to **stderr** (stdout carries the MCP protocol) and prints the backend
URL and the number of tool modules registered at startup.

---

## Extending it

Tools live in `mcp_server/tools/`, one module per domain. To add one:

1. Write the function inside the relevant module's `register()`.
2. Decorate it with `@mcp.tool()`.
3. Give it a **docstring** — the summary line and `Args:` block are what Claude
   reads to decide when and how to call it. Be explicit about slugs, formats
   and ordering requirements.
4. Add a case to `tests/test_mcp_server.py`.

For a whole new domain, add a module and list it in `MODULES` in
`mcp_server/tools/__init__.py`.
