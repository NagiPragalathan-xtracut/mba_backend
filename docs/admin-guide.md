# Admin guide

For anyone publishing content on the university website. No technical
background needed.

Sign in at **`/admin/`** with the username and password you were given.

## The dashboard

The landing page shows:

- **Content at a glance** — how many events, blogs, faculty profiles and
  departments exist, how many are live, and how many are hidden. Each card
  links straight to the list or to a blank "add" form.
- **Recently edited** — the last few things anyone changed, newest first, with
  a red *Draft* badge on anything not yet published.
- **Developer tools** — API documentation and access tokens.

The left sidebar groups everything: **Content** (Events, Blogs, Faculty),
**Taxonomy** (Departments, Categories, Designations) and **Access** (Users,
Groups, API Tokens).

## Before you start: set up the taxonomy

Departments, categories and designations are shared across the whole site, so
create them **once** and reuse them.

1. **Departments** — every academic department. Fill in the full name and a
   short form (`CSE`), and use *Display order* to control the order on the
   website.
2. **Event categories** — *Upcoming* and *Achievements* already exist. Add more
   only if the site genuinely needs another grouping.
3. **Blog categories** — topics such as Research, Campus Life, Placements.
4. **Designations** — job titles. *Display order* is handy for seniority
   (Head of Department above Professor, and so on).

The department list shows how much content uses each entry, so you can see at a
glance whether one is safe to retire.

## Adding an event

**Content → Events → Add Event.** The form is split into tabs.

**Event tab**
- *Title* — the name shown on the website.
- *Slug* — the web address. Fills itself in as you type the title; only change
  it if you have a reason, and never after the page is live (existing links
  would break).
- *Category* — Upcoming or Achievements.
- *Departments* — pick one or more, or leave empty for university-wide events.
- *Summary* — the teaser on listing cards. Leave it blank and the first part of
  the description is used.
- *Content* — the full description, in the rich-text editor. You can paste from
  Word, add headings, lists, links, tables and images.

**Schedule & Venue tab** — dates and location. For a single-day event fill only
*Event date*. The form refuses an end date earlier than the start date.

**Publishing tab**
- *Is published* — untick to hide the event from the website while you work.
- *Is featured* — highlight it on listing pages.
- *Display order* — lower numbers appear first.

**Photos** — the *Event Images* section at the bottom. Click **+ Add another**
for each photo. For each row set the image, alt text (a short description, used
by screen readers and search engines) and an optional caption.

> **The highlight photo.** Tick **Is featured** on the one photo that should
> represent the event on listing cards and social media. Only one photo per
> event can be featured — ticking a new one automatically unticks the old. If
> you tick nothing, the first photo is used.

Then **Save**.

## Adding a blog post

**Content → Blogs → Add Blog.**

- **Post tab** — title, slug, categories (more than one is fine), departments,
  summary and the article body.
- **Cover & Byline tab** — the cover image (used on listing cards *and* as the
  social-media preview), its alt text, the author name and the publication
  date.
- **Publishing tab** — same controls as events.
- **Blog Images** at the bottom — extra photos used inside the article. These
  are *not* the cover; the cover is on the Cover & Byline tab.

Blogs show an estimated reading time on the website, calculated from the
article length.

## Adding a faculty profile

**Content → Faculty → Add Faculty.**

- **Profile tab** — name, slug, designation, departments (a person can belong
  to more than one) and qualifications.
- **Photo tab** — the portrait. Portrait orientation works best.
- **Contact tab** — email, phone and an external profile link. All optional;
  anything you fill in is shown publicly.
- **Publishing tab** — same controls as events.

### Profile sections — the "+" button

A profile's written content is **not** a fixed form. Scroll to **Profile
Sections (click + to add another)** and add one block per topic:

| Heading | Content |
| --- | --- |
| Biography | A short professional bio |
| Publications | A list of papers |
| Awards | Recognitions received |
| Workshops | Workshops conducted or attended |
| Work Experience | Previous roles |
| Projects | Research or industry projects |
| Patents | Granted patents |

Click **+ Add another** for each one. Every block has:

- *Heading* — the section title. Must be unique within a profile.
- *Content* — rich text, so lists and links work.
- *Display order* — lower numbers appear first.
- *Is visible* — untick to hide a section without deleting it.

Use whatever headings suit the person — nothing is fixed. Two faculty members
can have completely different sets.

**Banners** below are optional wide images for the top of the profile page.

## The SEO tabs

Every content form has **Search Engine**, **Social Sharing** and **Structured
Data** tabs.

**You can ignore them.** Leave every field blank and the system fills them in
when you save — page title, search-result description, keywords, web address,
Facebook/LinkedIn/WhatsApp preview and the structured data Google uses. They
also stay in sync: rename an event and the generated title follows.

Fill one in only when you want something specific. Anything you type is kept
exactly as written and never overwritten, even when the content changes later.

Rough guide if you do write your own:

- *Meta title* — under 70 characters.
- *Meta description* — under 160 characters; this is the grey text under the
  link in Google results.
- *Structured Data* — leave this alone unless you know what JSON-LD is.

## Doing things in bulk

Tick the checkboxes on any list, choose an action from the dropdown and click
Go:

- Publish selected
- Unpublish selected
- Mark as featured
- Remove from featured

*Display order* can also be edited directly in the list — change several rows,
then click Save at the bottom.

## Finding things

- **Search** — the box above each list searches titles, summaries and body text.
- **Filters** — the right-hand panel filters by category, department, published
  state and more. Click **Apply** when you are done choosing.
- **Date navigation** — the year/month links above events and blogs.

## Good habits

1. **Always fill in alt text** on images. Screen readers and search engines
   both rely on it.
2. **Do not change a slug after publishing.** Links already shared would break.
3. **Unpublish instead of deleting.** Deleting is permanent and takes the
   photos with it; unticking *Is published* is reversible.
4. **Reuse departments and categories.** Creating a near-duplicate ("CSE" next
   to "Computer Science") splits the website's filters.
5. **Keep images reasonable.** Under about 1 MB; the limit is 10 MB.
6. **Use Save and continue editing** on long forms so nothing is lost.

The form warns you if you try to leave with unsaved changes.
