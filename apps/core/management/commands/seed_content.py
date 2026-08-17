"""
Populate the database with realistic sample content.

Useful for a fresh checkout, for demoing the admin, and for exercising the MCP
tools against non-empty data. Safe to run more than once - everything is keyed
on slug and updated in place rather than duplicated.

    python manage.py seed_content
    python manage.py seed_content --flush   # remove seeded rows first
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.blogs.models import Blog, BlogCategory
from apps.core.models import Department
from apps.events.models import Event, EventCategory
from apps.faculty.models import Designation, Faculty, FacultySection

DEPARTMENTS = [
    ("Computer Science & Engineering", "CSE", 10),
    ("Electronics & Communication Engineering", "ECE", 20),
    ("Mechanical Engineering", "MECH", 30),
    ("School of Management", "SOM", 40),
]

DESIGNATIONS = [
    ("Professor", 10),
    ("Associate Professor", 20),
    ("Assistant Professor", 30),
    ("Head of Department", 5),
]

BLOG_CATEGORIES = [
    ("Research", 10),
    ("Campus Life", 20),
    ("Placements", 30),
]

# Headings used for the repeatable faculty profile sections.
FACULTY_SECTIONS = [
    ("Biography", "<p>Over a decade of teaching and research experience across academia and industry.</p>", 10),
    ("Publications", "<ul><li>Sample journal paper, 2025.</li><li>Sample conference paper, 2024.</li></ul>", 20),
    ("Awards", "<p>Best Faculty Award, 2024.</p>", 30),
]


class Command(BaseCommand):
    help = "Create sample departments, categories, events, blogs and faculty."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete previously seeded content first.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        departments = self._seed_departments()
        designations = self._seed_designations()
        blog_categories = self._seed_blog_categories()
        self._seed_events(departments)
        self._seed_blogs(departments, blog_categories)
        self._seed_faculty(departments, designations)

        self.stdout.write(self.style.SUCCESS("\nSample content ready. Log into /admin/ to review it."))

    # ------------------------------------------------------------------

    def _flush(self):
        for model in (Faculty, Blog, Event):
            count, _ = model.objects.filter(slug__startswith="sample-").delete()
            self.stdout.write(f"Removed {count} seeded {model._meta.verbose_name_plural}.")

    def _seed_departments(self):
        departments = {}
        for name, short_name, order in DEPARTMENTS:
            department, _ = Department.objects.update_or_create(
                name=name,
                defaults={"short_name": short_name, "display_order": order, "is_active": True},
            )
            departments[short_name] = department
        self.stdout.write(f"Departments: {len(departments)}")
        return departments

    def _seed_designations(self):
        designations = {}
        for name, order in DESIGNATIONS:
            designation, _ = Designation.objects.update_or_create(
                name=name, defaults={"display_order": order, "is_active": True}
            )
            designations[name] = designation
        self.stdout.write(f"Designations: {len(designations)}")
        return designations

    def _seed_blog_categories(self):
        categories = {}
        for name, order in BLOG_CATEGORIES:
            category, _ = BlogCategory.objects.update_or_create(
                name=name, defaults={"display_order": order, "is_active": True}
            )
            categories[name] = category
        self.stdout.write(f"Blog categories: {len(categories)}")
        return categories

    def _seed_events(self, departments):
        # The two default categories come from the events data migration.
        upcoming = EventCategory.objects.get(slug="upcoming")
        achievements = EventCategory.objects.get(slug="achievements")
        today = timezone.localdate()

        specs = [
            {
                "slug": "sample-tech-symposium-2026",
                "title": "National Tech Symposium 2026",
                "category": upcoming,
                "departments": [departments["CSE"], departments["ECE"]],
                "content": "<p>A two-day symposium on applied AI, embedded systems and robotics.</p>",
                "event_date": today + timedelta(days=45),
                "end_date": today + timedelta(days=46),
                "venue": "Main Auditorium",
                "display_order": 10,
            },
            {
                "slug": "sample-smart-india-hackathon-win",
                "title": "Students Win Smart India Hackathon",
                "category": achievements,
                "departments": [departments["CSE"]],
                "content": "<p>A student team took first place in the national grand finale.</p>",
                "event_date": today - timedelta(days=30),
                "venue": "New Delhi",
                "display_order": 20,
            },
        ]

        for spec in specs:
            department_list = spec.pop("departments")
            event, _ = Event.objects.update_or_create(slug=spec["slug"], defaults=spec)
            event.departments.set(department_list)
            # Relations are written after the row, so refresh the SEO values
            # that depend on them (this is what the admin and API also do).
            event.sync_related_seo()
        self.stdout.write(f"Events: {len(specs)}")

    def _seed_blogs(self, departments, categories):
        specs = [
            {
                "slug": "sample-life-on-campus",
                "title": "A Week in the Life of a First-Year Student",
                "content": "<p>Classes, clubs, labs and everything in between.</p>",
                "author_name": "Student Affairs",
                "categories": [categories["Campus Life"]],
                "departments": [],
                "display_order": 10,
            },
            {
                "slug": "sample-placement-season-recap",
                "title": "Placement Season 2026: What Changed",
                "content": "<p>Recruiter mix, roles offered and how students prepared.</p>",
                "author_name": "Training & Placement Cell",
                "categories": [categories["Placements"]],
                "departments": [departments["CSE"], departments["SOM"]],
                "display_order": 20,
            },
        ]

        for spec in specs:
            category_list = spec.pop("categories")
            department_list = spec.pop("departments")
            blog, _ = Blog.objects.update_or_create(slug=spec["slug"], defaults=spec)
            blog.categories.set(category_list)
            blog.departments.set(department_list)
            blog.sync_related_seo()
        self.stdout.write(f"Blogs: {len(specs)}")

    def _seed_faculty(self, departments, designations):
        specs = [
            {
                "slug": "sample-dr-anitha-rao",
                "name": "Dr. Anitha Rao",
                "designation": designations["Professor"],
                "departments": [departments["CSE"]],
                "qualification": "Ph.D., M.Tech, B.Tech",
                "mail_id": "anitha.rao@example.edu",
                "display_order": 10,
            },
            {
                "slug": "sample-dr-vikram-menon",
                "name": "Dr. Vikram Menon",
                "designation": designations["Associate Professor"],
                "departments": [departments["ECE"], departments["MECH"]],
                "qualification": "Ph.D., M.E.",
                "display_order": 20,
            },
        ]

        for spec in specs:
            department_list = spec.pop("departments")
            faculty, _ = Faculty.objects.update_or_create(slug=spec["slug"], defaults=spec)
            faculty.departments.set(department_list)
            for heading, content, order in FACULTY_SECTIONS:
                FacultySection.objects.update_or_create(
                    faculty=faculty,
                    heading=heading,
                    defaults={"content": content, "display_order": order},
                )
            faculty.sync_related_seo()
        self.stdout.write(f"Faculty: {len(specs)} (each with {len(FACULTY_SECTIONS)} profile sections)")
