"""Tests for faculty profiles and their repeatable sections."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.core.models import Department
from apps.faculty.models import Designation, Faculty, FacultySection


class FacultyModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.designation = Designation.objects.create(name="Professor")
        cls.cse = Department.objects.create(name="Computer Science", short_name="CSE")
        cls.ece = Department.objects.create(name="Electronics", short_name="ECE")

    def make_faculty(self, name="Dr. Anitha Rao", **overrides):
        return Faculty.objects.create(name=name, designation=self.designation, **overrides)

    def test_slug_comes_from_the_name_not_a_title_field(self):
        self.assertEqual(self.make_faculty().slug, "dr-anitha-rao")

    def test_image_alt_defaults_to_the_name(self):
        self.assertEqual(self.make_faculty().image_alt, "Dr. Anitha Rao")

    def test_str_includes_the_designation(self):
        self.assertEqual(str(self.make_faculty()), "Dr. Anitha Rao - Professor")

    def test_a_person_can_belong_to_several_departments(self):
        faculty = self.make_faculty()
        faculty.departments.set([self.cse, self.ece])
        self.assertEqual(faculty.department_names, ["Computer Science", "Electronics"])

    def test_schema_lists_every_department_as_an_affiliation(self):
        faculty = self.make_faculty(mail_id="a@example.edu")
        faculty.departments.set([self.cse, self.ece])
        faculty.sync_related_seo()
        faculty.refresh_from_db()

        names = [entry["name"] for entry in faculty.schema_json["affiliation"]]
        self.assertEqual(names, ["Computer Science", "Electronics"])
        self.assertEqual(faculty.schema_json["@type"], "Person")
        self.assertEqual(faculty.schema_json["email"], "a@example.edu")

    def test_seo_description_combines_designation_and_qualification(self):
        faculty = self.make_faculty(qualification="Ph.D., M.Tech")
        self.assertIn("Professor", faculty.meta_description)
        self.assertIn("Ph.D., M.Tech", faculty.meta_description)

    def test_phone_number_is_validated(self):
        faculty = Faculty(name="Dr. Bad Phone", designation=self.designation, phone_number="not-a-number!!")
        with self.assertRaises(ValidationError):
            faculty.full_clean()


class FacultySectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.designation = Designation.objects.create(name="Professor")

    def setUp(self):
        self.faculty = Faculty.objects.create(name="Dr. Vikram Menon", designation=self.designation)

    def test_sections_are_ordered_by_display_order(self):
        FacultySection.objects.create(faculty=self.faculty, heading="Awards", content="<p>a</p>", display_order=30)
        FacultySection.objects.create(faculty=self.faculty, heading="Biography", content="<p>b</p>", display_order=10)
        FacultySection.objects.create(faculty=self.faculty, heading="Publications", content="<p>c</p>", display_order=20)

        headings = list(self.faculty.sections.values_list("heading", flat=True))
        self.assertEqual(headings, ["Biography", "Publications", "Awards"])

    def test_a_profile_cannot_have_two_sections_with_the_same_heading(self):
        FacultySection.objects.create(faculty=self.faculty, heading="Awards", content="<p>a</p>")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FacultySection.objects.create(faculty=self.faculty, heading="Awards", content="<p>b</p>")

    def test_different_profiles_may_reuse_a_heading(self):
        other = Faculty.objects.create(name="Dr. Priya Sharma", designation=self.designation)
        FacultySection.objects.create(faculty=self.faculty, heading="Awards", content="<p>a</p>")
        FacultySection.objects.create(faculty=other, heading="Awards", content="<p>b</p>")
        self.assertEqual(FacultySection.objects.filter(heading="Awards").count(), 2)

    def test_deleting_a_profile_removes_its_sections(self):
        FacultySection.objects.create(faculty=self.faculty, heading="Awards", content="<p>a</p>")
        self.faculty.delete()
        self.assertEqual(FacultySection.objects.count(), 0)

    def test_first_section_feeds_the_seo_description(self):
        FacultySection.objects.create(
            faculty=self.faculty, heading="Biography",
            content="<p>Leads the robotics research group.</p>", display_order=1,
        )
        self.faculty.meta_description = ""
        self.faculty.seo_generated = {}
        self.faculty.save()
        self.assertIn("Leads the robotics research group", self.faculty.meta_description)
