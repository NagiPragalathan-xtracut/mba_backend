"""
Load the SRM B-School website's content into the backend.

`seed_content` creates generic sample rows for exploring the admin. This
command is different: it loads the *actual* content the marketing site is
currently showing - the four news entries, the six blog posts and the full
faculty roster - so the website can be switched from its hardcoded arrays to
this API without anything on the page changing.

    python manage.py seed_srmmba
    python manage.py seed_srmmba --flush   # remove these rows first

Safe to run repeatedly: every row is keyed on its slug and updated in place.
"""

from datetime import date, time

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.blogs.models import Blog, BlogCategory
from apps.core.models import Course, Department
from apps.events.models import Event, EventCategory
from apps.faculty.models import Designation, Faculty

#: Everything this command creates carries this slug prefix, which is what
#: `--flush` keys on. Faculty are excluded - their slugs are people's names.
SLUG_PREFIX = "srm-"

DEPARTMENT = ("School of Management", "SOM", 40)

FACULTY_PHOTO_BASE = "https://s3.ap-south-1.amazonaws.com/cdn.mba.srmrmp.edu.in/faculty/"

#: Categories the backend ships with that the SRM sidebar does not offer. They
#: are deactivated rather than deleted - see `_retire_unused_categories`.
UNUSED_EVENT_CATEGORIES = ("upcoming", "achievements")


def _paragraphs(*texts: str) -> str:
    """Wrap plain paragraphs as the HTML CKEditor would have produced."""
    return "".join(f"<p>{text}</p>" for text in texts)


# --------------------------------------------------------------------------
# News & events - the cards on /news-events
# --------------------------------------------------------------------------

NEWS_EVENTS = [
    {
        "slug": "srm-drug-awareness-programme",
        "courses": ["mba"],
        "title": "Drug Awareness Programme",
        "category": "events",
        "event_date": date(2024, 12, 18),
        "start_time": time(10, 0),
        "end_time": time(11, 0),
        "venue": "Seminar Hall",
        "display_order": 10,
        "summary": (
            "The Department of Biotechnology, with the NSS, held a session on the risks "
            "and consequences of substance abuse."
        ),
        "content": _paragraphs(
            "The Department of Biotechnology, in association with the National Service Scheme (NSS), "
            "organized a Drug Awareness Programme to educate students about the risks and consequences "
            "of substance abuse. The session emphasized the importance of making informed choices, "
            "promoting healthy lifestyles, and creating awareness about the social and personal impact "
            "of drug addiction.",
            "Expert speakers from the medical and counselling field addressed the gathering, sharing "
            "real-life case studies and statistics on substance abuse among youth. Interactive sessions "
            "allowed students to ask questions and engage directly with professionals, helping them "
            "understand the physical, psychological, and social consequences of drug dependency.",
            "The programme concluded with a pledge-taking ceremony where students committed to staying "
            "drug-free and spreading awareness in their communities. The institution reaffirmed its "
            "dedication to holistic student well-being and pledged to conduct more such awareness "
            "initiatives throughout the academic year.",
        ),
    },
    {
        "slug": "srm-annual-management-conclave-2024",
        "courses": ["mba", "executive-mba"],
        "title": "Annual Management Conclave 2024",
        "category": "events",
        "event_date": date(2024, 12, 12),
        "start_time": time(9, 0),
        "end_time": time(17, 0),
        "venue": "Main Auditorium",
        "display_order": 20,
        "summary": (
            "Industry leaders, academicians and students met to discuss emerging trends in "
            "business management."
        ),
        "content": _paragraphs(
            "The Annual Management Conclave brought together industry leaders, academicians, and students "
            "to discuss emerging trends in business management. The event featured keynote sessions, panel "
            "discussions, and networking opportunities that provided valuable insights into the evolving "
            "business landscape.",
            "Distinguished speakers from Fortune 500 companies and renowned academic institutions delivered "
            "sessions on topics including digital transformation, sustainable business practices, and "
            "leadership in the age of AI. Students gained first-hand perspectives on what the industry "
            "expects from future business leaders.",
            "The conclave also featured a case study competition where student teams presented innovative "
            "business solutions to a panel of industry judges. The event ended with an awards ceremony "
            "recognising outstanding academic achievement and extracurricular contributions across the "
            "MBA program.",
        ),
    },
    {
        "slug": "srm-ranked-among-top-50-b-schools",
        "courses": ["mba"],
        "title": "SRM B-School Ranked Among Top 50 B-Schools in India",
        "category": "news",
        "event_date": date(2024, 12, 10),
        "display_order": 30,
        "summary": (
            "A leading national ranking agency has placed SRM B-School among the country's "
            "top 50 business schools."
        ),
        "content": _paragraphs(
            "SRM B-School has been ranked among the top 50 business schools in India by a leading national "
            "ranking agency. This recognition reflects the institution's commitment to academic excellence, "
            "industry integration, and holistic student development. The ranking considered parameters "
            "including faculty quality, placements, research output, and industry connect.",
            "The ranking methodology evaluated over 300 business schools across India, assessing factors "
            "such as curriculum innovation, international collaborations, alumni impact, and infrastructure. "
            "SRM B-School scored particularly high in placement outcomes and faculty research contributions, "
            "reflecting its strong industry partnerships.",
            "The Dean of SRM B-School expressed pride in this achievement and attributed the success to the "
            "collective efforts of students, faculty, and the administrative team. The institution aims to "
            "further strengthen its position by launching new specialisations and expanding its global "
            "exchange programmes in the coming academic year.",
        ),
    },
    {
        "slug": "srm-mba-admissions-open-2025",
        "courses": ["mba", "executive-mba", "mba-finance", "mba-marketing", "mba-hr", "mba-operations"],
        "title": "MBA Admissions Open for 2025 Batch",
        "category": "announcements",
        "event_date": date(2024, 12, 8),
        "display_order": 40,
        "summary": (
            "Applications are now open for the 2025 MBA batch. Selection is by written test, "
            "group discussion and interview."
        ),
        "content": _paragraphs(
            "SRM B-School is pleased to announce that admissions are now open for the MBA program for the "
            "2025 academic batch. Eligible candidates with a bachelor's degree in any discipline are "
            "invited to apply. The selection process includes a written test, group discussion, and "
            "personal interview. Early applications are encouraged as seats are limited.",
            "The MBA program at SRM B-School offers specialisations in Finance, Marketing, Human Resources, "
            "Operations, and Business Analytics. Students benefit from a rigorous curriculum co-designed "
            "with industry experts, ensuring alignment with current market demands and equipping graduates "
            "with the skills needed to excel in competitive environments.",
            "Scholarship opportunities are available for meritorious candidates based on academic "
            "performance and entrance test scores. Interested applicants can visit the admissions portal "
            "for detailed eligibility criteria, important dates, and application guidelines. The admissions "
            "team is available to assist candidates throughout the process.",
        ),
    },
]


# --------------------------------------------------------------------------
# Blogs - the slider on /news-events
# --------------------------------------------------------------------------

BLOGS = [
    {
        "slug": "srm-future-of-mba-education",
        "courses": ["mba"],
        "title": "The Future of MBA Education in a Digital World",
        "category": "leadership",
        "published_date": date(2025, 1, 15),
        "display_order": 10,
        "summary": (
            "As technology reshapes every industry, MBA programs must evolve to prepare leaders who are "
            "not only business-savvy but also digitally fluent. Explore how top B-Schools are integrating "
            "AI, data analytics, and digital strategy into their core curriculum."
        ),
        "content": _paragraphs(
            "The rapid acceleration of digital technologies has fundamentally altered how businesses "
            "operate, compete, and create value. For MBA programs, this shift represents both a challenge "
            "and an opportunity - the challenge of keeping pace with a constantly evolving landscape, and "
            "the opportunity to equip the next generation of leaders with skills that are truly "
            "future-ready.",
            "Leading business schools around the world are responding by embedding digital literacy into "
            "the core of their MBA curriculum. Courses in artificial intelligence, machine learning, data "
            "analytics, and digital strategy are no longer elective add-ons but essential components of a "
            "well-rounded management education. Students who graduate with a strong grasp of these tools "
            "are far better positioned to drive transformation in the organisations they join.",
            "Beyond technical skills, the future of MBA education lies in developing adaptive thinking - "
            "the ability to navigate ambiguity, pivot strategies in real time, and lead teams through "
            "continuous change. As industries converge and traditional business boundaries blur, the MBA "
            "graduates of tomorrow will need to be as comfortable in a boardroom as they are in a data lab.",
            "SRM B-School is committed to this vision. Through collaborations with technology companies, "
            "live industry projects, and a curriculum that integrates digital tools with management "
            "fundamentals, we are preparing our students not just for the jobs of today, but for the "
            "challenges and opportunities of the decade ahead.",
        ),
    },
    {
        "slug": "srm-ace-your-mba-interview",
        "courses": ["mba", "executive-mba"],
        "title": "How to Ace Your MBA Interview: Tips from Industry Experts",
        "category": "career",
        "published_date": date(2025, 1, 10),
        "display_order": 20,
        "summary": (
            "Cracking an MBA admission interview requires more than academic excellence. Industry experts "
            "share insider tips on how to articulate your vision, demonstrate leadership potential, and "
            "stand out in a competitive applicant pool."
        ),
        "content": _paragraphs(
            "The MBA admission interview is often the final - and most decisive - stage of the selection "
            "process. Unlike entrance exams that test academic aptitude, the interview evaluates your "
            "personality, clarity of purpose, and leadership potential. Understanding what interviewers "
            "are truly looking for can make the difference between an acceptance letter and a rejection.",
            "Industry experts consistently highlight the importance of a compelling personal narrative. "
            "Your story should connect your past experiences, present motivations, and future goals in a "
            "coherent and authentic way. Interviewers are not simply assessing your credentials - they are "
            "assessing whether you can communicate your vision with confidence and conviction.",
            "Preparation is equally critical. Research the institution thoroughly - its faculty, "
            "specialisations, alumni network, and recent achievements. Be ready to explain why this "
            "particular program aligns with your career goals, and come prepared with specific examples "
            "that demonstrate your leadership, problem-solving, and teamwork abilities.",
            "Finally, remember that an interview is a two-way conversation. Asking thoughtful questions "
            "about the program signals genuine interest and intellectual curiosity. The most successful "
            "candidates approach the interview not as an interrogation but as a dialogue - one in which "
            "they are equally evaluating whether the institution is the right fit for their ambitions.",
        ),
    },
    {
        "slug": "srm-top-5-skills-mba-graduates-2025",
        "courses": ["mba"],
        "title": "Top 5 Skills Every MBA Graduate Needs in 2025",
        "category": "industry",
        "published_date": date(2025, 1, 5),
        "display_order": 30,
        "summary": (
            "The business landscape is changing faster than ever. From emotional intelligence to data "
            "literacy, we break down the five essential skills that employers are actively seeking in "
            "MBA graduates entering the workforce in 2025."
        ),
        "content": _paragraphs(
            "The expectations placed on MBA graduates have never been higher. Employers in 2025 are not "
            "just looking for candidates who can analyse financial statements or draft a marketing plan - "
            "they want versatile leaders who can navigate complexity, inspire teams, and deliver results "
            "in an environment defined by constant disruption.",
            "Data literacy tops the list of in-demand skills. The ability to interpret data, draw "
            "meaningful insights, and translate those insights into actionable business decisions is now a "
            "baseline expectation across all industries. MBA graduates who can bridge the gap between "
            "quantitative analysis and strategic thinking are consistently among the most sought-after "
            "candidates.",
            "Emotional intelligence - the capacity to understand and manage one's own emotions while "
            "empathising with others - has emerged as equally critical. Research consistently shows that "
            "high EQ is a stronger predictor of leadership effectiveness than IQ alone. As workplaces "
            "become more diverse and collaborative, the ability to build trust and navigate interpersonal "
            "dynamics is invaluable.",
            "Rounding out the essential skill set are adaptability, cross-functional communication, and "
            "sustainability literacy. Businesses today expect their leaders to move fluidly across "
            "functions, communicate clearly with stakeholders at all levels, and make decisions that "
            "account for environmental and social impact alongside financial returns. MBA graduates who "
            "cultivate these competencies will be well-equipped to lead in any industry.",
        ),
    },
    {
        "slug": "srm-day-in-the-life-mba-student",
        "courses": ["mba"],
        "title": "A Day in the Life of an SRM B-School MBA Student",
        "category": "campus-life",
        "published_date": date(2024, 12, 28),
        "display_order": 40,
        "summary": (
            "From morning lectures and industry workshops to networking events and sports activities, "
            "discover what a typical day looks like for an MBA student at SRM B-School - a vibrant campus "
            "where learning never stops."
        ),
        "content": _paragraphs(
            "Life as an MBA student at SRM B-School is anything but ordinary. The day typically begins "
            "early - with many students gathering for informal study sessions or group discussions before "
            "the first lecture. The campus comes alive quickly, buzzing with the energy of students who "
            "are deeply invested in making the most of every opportunity.",
            "Morning sessions are often dedicated to core subjects: strategy, finance, marketing, or "
            "operations. Professors bring real-world experience into the classroom, drawing on case "
            "studies, live data, and industry examples to make concepts tangible and relevant. Guest "
            "lectures from senior industry professionals are a regular feature, offering students direct "
            "access to practitioner insights.",
            "Afternoons are typically more varied. Committee meetings, club activities, industry visits, "
            "and internship-related work fill the schedule. Student-led bodies organise a wide range of "
            "events - from entrepreneurship bootcamps to cultural festivals - ensuring that the MBA "
            "experience extends well beyond the classroom.",
            "Evenings on campus are a time for reflection, networking, and personal development. Whether "
            "it's a casual conversation with a batchmate that sparks a business idea, a mentorship session "
            "with a faculty member, or simply unwinding on the sports field, the SRM B-School campus offers "
            "an environment where growth happens at every hour of the day.",
        ),
    },
    {
        "slug": "srm-sustainability-and-business",
        "courses": ["mba", "mba-operations"],
        "title": "Sustainability and Business: The New Corporate Mandate",
        "category": "research",
        "published_date": date(2024, 12, 20),
        "display_order": 50,
        "summary": (
            "ESG - Environmental, Social, and Governance - is no longer a buzzword but a business "
            "imperative. Learn how forward-thinking companies are embedding sustainability into their core "
            "strategies and what this means for the next generation of business leaders."
        ),
        "content": _paragraphs(
            "The relationship between business and sustainability has undergone a fundamental "
            "transformation over the past decade. What was once considered a peripheral concern - a matter "
            "of corporate social responsibility or public relations - has become a central pillar of "
            "business strategy. Investors, customers, regulators, and employees are all demanding that "
            "organisations demonstrate a genuine commitment to environmental and social responsibility.",
            "The ESG framework - encompassing Environmental, Social, and Governance considerations - has "
            "emerged as the primary lens through which businesses are evaluated on their sustainability "
            "commitments. Companies that score well on ESG metrics are increasingly rewarded with lower "
            "costs of capital, stronger brand loyalty, and greater resilience in the face of regulatory "
            "and market disruptions.",
            "For MBA graduates entering the workforce, sustainability literacy is no longer optional. "
            "Understanding how to integrate ESG principles into business decision-making, measure and "
            "report sustainability performance, and engage with diverse stakeholders on these issues is "
            "now an essential management competency. The most forward-thinking organisations are actively "
            "seeking leaders who can drive the transition to more sustainable business models.",
            "At SRM B-School, sustainability is woven into both the curriculum and the campus culture. "
            "Through dedicated courses, research initiatives, and partnerships with organisations at the "
            "forefront of the sustainability movement, we are equipping our students to become the "
            "responsible business leaders that the world urgently needs.",
        ),
    },
    {
        "slug": "srm-understanding-fintech",
        "courses": ["mba-finance", "mba"],
        "title": "Understanding Fintech: Opportunities for MBA Graduates",
        "category": "finance",
        "published_date": date(2024, 12, 12),
        "display_order": 60,
        "summary": (
            "The fintech revolution is creating new career pathways for MBA graduates. From blockchain to "
            "digital payments and neo-banking, we explore the emerging roles that are transforming the "
            "finance industry and how an MBA can position you for success."
        ),
        "content": _paragraphs(
            "The financial services industry is in the midst of its most profound transformation in a "
            "generation. Driven by advances in mobile technology, artificial intelligence, and blockchain, "
            "fintech companies are dismantling traditional banking models and creating entirely new ways "
            "for individuals and businesses to access, manage, and grow their money.",
            "For MBA graduates with an interest in finance, this revolution represents an extraordinary "
            "opportunity. The fintech sector is hungry for professionals who combine financial acumen with "
            "an understanding of technology, customer experience, and regulatory frameworks. Roles in "
            "product management, risk analytics, digital strategy, and venture capital are expanding "
            "rapidly, and many of these positions are specifically designed for candidates with MBA-level "
            "qualifications.",
            "Blockchain and decentralised finance (DeFi) are among the most disruptive forces reshaping "
            "the industry. Understanding these technologies - not just how they work, but how they create "
            "and destroy value - is becoming an increasingly important competency for finance "
            "professionals. MBA programs that address these topics equip graduates to participate "
            "meaningfully in conversations that are defining the future of global finance.",
            "The key to success in fintech lies in the ability to bridge worlds: to translate complex "
            "financial concepts for technology teams, and to communicate technical possibilities to "
            "business stakeholders. MBA graduates who cultivate this bilingual fluency - combining "
            "financial expertise with technological curiosity - will find themselves at the forefront of "
            "one of the most dynamic sectors in the global economy.",
        ),
    },
]


# --------------------------------------------------------------------------
# Faculty roster - (name, designation, photo file on the CDN)
# --------------------------------------------------------------------------

FACULTY = [
    ("Dr. S. Praveen Kumar", "Professor / Dean", "Dr.+S.+Praveen+Kumar.png"),
    ("Dr. R. Arulmoli", "Professor & HOD - MBA", "Dr.+R.+Arulmoli_.png"),
    ("Dr. S. Vijayarani", "Associate Professor", "Dr.+S.+Vijayarani.png"),
    ("Dr. K. Priya", "Associate Professor", "Dr.+K.+Priya_.png"),
    ("Dr. G. Aravindhan", "Associate Professor", "Dr.+G.+Aravindhan.png"),
    ("Dr. K. Prakash", "Assistant Professor (Sr. Grade)", "Dr.+K.+Prakash_.png"),
    ("Dr. S. Ramanathan", "Assistant Professor (Sr. Grade)", "Dr.+Ramanathan.png"),
    ("Dr. V. Sivakamy", "Assistant Professor", "Dr.+Sivakamy+V.png"),
    ("Dr. S. Lakshmi", "Assistant Professor", "Dr.+S.+Lakshmi.png"),
    ("Dr. Anto Praveen Singh", "Assistant Professor", "Dr.+Anto+Pravin+Singh_.png"),
    ("Dr. A. L. Chidambaram", "Assistant Professor", "Dr.+Chidambaram.png"),
    ("Dr. S. Loganatha Prasanna", "Assistant Professor", "Dr.+Loganatha+Prasanna_.png"),
    ("Dr. P. Subha", "Assistant Professor", "Dr.+P.+Subha_.png"),
    ("Dr. R. Sharmila Devi", "Assistant Professor", "Dr.+R.+Sharmila+Devi_.png"),
    ("Dr. V. Susan Jeyaseeli", "Assistant Professor", "Dr.+Susan+Jayaseeli+Manuel_.png"),
    ("Dr. P. Mohanraj", "Assistant Professor", "Dr.+P.+Mohan+Raj_.png"),
    ("Mrs. Kavitha Bagilesh", "Assistant Professor", "Kavitha+Bagilesh.png"),
    ("Dr. Prasad Babu", "Assistant Professor", "Dr.+P.+Prasad+Babu_.png"),
    ("Dr. D. Manimegalai", "Assistant Professor", "Dr.+D.+Manimegalai_.png"),
    ("Dr. Jeffrey Jim", "Assistant Professor", "Dr.+Jeffrey+Jim+Salvius_.png"),
    ("Mrs. Latha", "Assistant Professor", ""),
    ("Dr. Rabuni Aiswarya", "Assistant Professor", "Dr.+Rabuni+Aiswarya_.png"),
    ("Mr. Jeswanth", "Assistant Professor", "Mr.+Jaswant+Sesha+Sai_.png"),
    ("Dr. Asha K.", "Assistant Professor", ""),
    ("Dr. Revathy", "Assistant Professor", "Dr.+Revathy_.png"),
    ("Ms. Aakifa Siddiqua S. T.", "Research Scholar", "Aakifa.png"),
    ("Mr. Adithya", "Research Scholar", "Mr.+Adhitya.png"),
]

#: Seniority order for the designations above, so the directory lists the Dean
#: first and research scholars last - the order the current website uses.
DESIGNATION_ORDER = {
    "Professor / Dean": 10,
    "Professor & HOD - MBA": 20,
    "Associate Professor": 30,
    "Assistant Professor (Sr. Grade)": 40,
    "Assistant Professor": 50,
    "Research Scholar": 60,
}


class Command(BaseCommand):
    help = "Load the SRM B-School website content (news, events, blogs and faculty)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete the content this command previously created before reloading it.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        department = self._seed_department()
        self._retire_unused_categories()
        self._seed_news_events(department)
        self._seed_blogs(department)
        self._seed_faculty(department)

        self.stdout.write(self.style.SUCCESS("\nSRM B-School content loaded. Review it at /admin/."))

    # ------------------------------------------------------------------

    def _flush(self):
        for model in (Blog, Event):
            count, _ = model.objects.filter(slug__startswith=SLUG_PREFIX).delete()
            self.stdout.write(f"Removed {count} {model._meta.verbose_name_plural}.")
        # Faculty slugs come from people's names, so they are matched by name.
        count, _ = Faculty.objects.filter(name__in=[name for name, _, _ in FACULTY]).delete()
        self.stdout.write(f"Removed {count} faculty profiles.")

    def _retire_unused_categories(self):
        """
        Hide the categories the SRM site's sidebar does not offer.

        "Upcoming" and "Achievements" ship with the backend as generic
        editorial buckets. The SRM design filters by News / Events /
        Announcements / Press Release / Campus Life instead, and the sidebar is
        built from whatever categories are active - so leaving these on would
        add two entries the design does not have. They are deactivated, not
        deleted: an editor can tick "Is active" in the admin to bring them back.
        """
        retired = EventCategory.objects.filter(slug__in=UNUSED_EVENT_CATEGORIES).update(is_active=False)
        if retired:
            self.stdout.write(
                f"Deactivated {retired} unused event categories "
                f"({', '.join(UNUSED_EVENT_CATEGORIES)}) - re-enable them in the admin if needed."
            )

    def _seed_department(self):
        name, short_name, order = DEPARTMENT
        department, _ = Department.objects.update_or_create(
            name=name,
            defaults={"short_name": short_name, "display_order": order, "is_active": True},
        )
        self.stdout.write(f"Department: {department.name}")
        return department

    def _courses_by_slug(self):
        """Course lookup, seeded by the core/0003_default_courses migration."""
        return {course.slug: course for course in Course.objects.all()}

    def _resolve_courses(self, courses, slugs):
        """Course objects for ``slugs``, failing loudly on an unknown one."""
        resolved = []
        for slug in slugs:
            course = courses.get(slug)
            if course is None:
                raise ValueError(
                    f"Course '{slug}' does not exist. Run `python manage.py migrate` first."
                )
            resolved.append(course)
        return resolved

    def _seed_news_events(self, department):
        # These category slugs are created by the events data migrations, so a
        # missing one means migrations have not been applied.
        categories = {category.slug: category for category in EventCategory.objects.all()}
        courses = self._courses_by_slug()

        for spec in NEWS_EVENTS:
            spec = dict(spec)
            course_slugs = spec.pop("courses", [])
            category_slug = spec.pop("category")
            category = categories.get(category_slug)
            if category is None:
                raise ValueError(
                    f"Event category '{category_slug}' does not exist. Run `python manage.py migrate` first."
                )

            event, _ = Event.objects.update_or_create(
                slug=spec["slug"], defaults={**spec, "category": category}
            )
            event.departments.set([department])
            event.courses.set(self._resolve_courses(courses, course_slugs))
            # Relations are written after the row, so the SEO values that depend
            # on them have to be recomputed - same as the admin and API do.
            event.sync_related_seo()

        self.stdout.write(f"News & events: {len(NEWS_EVENTS)}")

    def _seed_blogs(self, department):
        categories = {category.slug: category for category in BlogCategory.objects.all()}
        courses = self._courses_by_slug()

        for spec in BLOGS:
            spec = dict(spec)
            course_slugs = spec.pop("courses", [])
            category_slug = spec.pop("category")
            category = categories.get(category_slug)
            if category is None:
                raise ValueError(
                    f"Blog category '{category_slug}' does not exist. Run `python manage.py migrate` first."
                )

            blog, _ = Blog.objects.update_or_create(
                slug=spec["slug"], defaults={**spec, "author_name": "SRM B-School"}
            )
            blog.categories.set([category])
            blog.departments.set([department])
            blog.courses.set(self._resolve_courses(courses, course_slugs))
            blog.sync_related_seo()

        self.stdout.write(f"Blogs: {len(BLOGS)}")

    def _seed_faculty(self, department):
        designations = {}
        for title, order in DESIGNATION_ORDER.items():
            designation, _ = Designation.objects.update_or_create(
                name=title, defaults={"display_order": order, "is_active": True}
            )
            designations[title] = designation

        for index, (name, title, photo) in enumerate(FACULTY):
            faculty, _ = Faculty.objects.update_or_create(
                name=name,
                defaults={
                    "designation": designations[title],
                    "external_image_url": f"{FACULTY_PHOTO_BASE}{photo}" if photo else "",
                    # Preserve the roster order the website currently shows.
                    "display_order": (index + 1) * 10,
                    "is_published": True,
                },
            )
            faculty.departments.set([department])
            faculty.sync_related_seo()

        self.stdout.write(f"Faculty: {len(FACULTY)} across {len(designations)} designations")
