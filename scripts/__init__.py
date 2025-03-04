from django.db import transaction

from apps.spider.models import CrawledData

# from apps.spider.tasks import crawl_medians, crawl_orc, crawl_timetable
from apps.spider.tasks import crawl_orc
from apps.spider.utils import retrieve_soup
from apps.web.models import Course, CourseOffering, Instructor
from lib.constants import CURRENT_TERM
from website.celery import app


def crawl_and_import_data():
    old_task_always_eager = app.conf.task_always_eager
    app.conf.task_always_eager = True

    # ORC crawling takes a long time, especially when run synchronously.
    # If the ORC is not crawled, the course selection will only be limited,
    # but this should not interfere with development
    print("Crawling ORC. This will take a while.")
    crawl_orc()

    # print("Crawling timetable")
    # crawl_timetable()

    # print("Crawling medians")
    # crawl_medians()

    print("Importing ORC")
    _import_crawled_datas(CrawledData.ORC_DEPARTMENT_COURSES)

    # print("Importing timetable")
    # _import_crawled_datas(CrawledData.COURSE_TIMETABLE)

    # print("Importing medians")
    # _import_crawled_datas(CrawledData.MEDIANS)

    app.conf.task_always_eager = old_task_always_eager


def _import_crawled_datas(data_type):
    for crawled_data in CrawledData.objects.filter(data_type=data_type):
        if crawled_data.has_change():
            crawled_data.approve_change()


# WARNING: Only use when already have course data but not instructor data


def crawl_and_save_instructors():
    """
    Crawl instructor data for all courses and save to database without modifying course data.
    This function can be run from the Django shell with:

    from scripts import crawl_and_save_instructors
    crawl_and_save_instructors()
    """
    # Base URL for course pages
    COURSE_DETAIL_URL_PREFIX = "https://www.ji.sjtu.edu.cn/academics/courses/courses-by-number/course-info/?id="

    # Get all courses with URLs
    courses = Course.objects.filter(url__isnull=False).exclude(url="")
    print(f"Found {courses.count()} courses with URLs")

    instructor_count = 0
    association_count = 0

    for course in courses:
        print(f"Processing {course.course_code}: {course.course_title}")

        # Skip if URL doesn't match expected pattern
        if not course.url or not course.url.startswith(COURSE_DETAIL_URL_PREFIX):
            print(f"  Skipping - invalid URL: {course.url}")
            continue

        # Extract instructors
        try:
            # Retrieve and parse the course page
            soup = retrieve_soup(course.url)
            children = list(soup.find_all(class_="et_pb_text_inner")[3].children)

            # Find instructors section
            instructor_names = []
            for i, child in enumerate(children):
                text = child.get_text(strip=True) if hasattr(child, "get_text") else ""
                if "Instructors:" in text:
                    instructors_text = (
                        children[i + 2].get_text(strip=True)
                        if i + 2 < len(children)
                        else ""
                    )
                    instructor_names = [
                        name.strip()
                        for name in instructors_text.split(";")
                        if name.strip()
                    ]
                    break

            if not instructor_names:
                print(f"  No instructors found")
                continue

            print(f"  Found instructors: {', '.join(instructor_names)}")

            # Get or create course offering for current term
            with transaction.atomic():
                offering, created = CourseOffering.objects.get_or_create(
                    course=course,
                    term=CURRENT_TERM,
                    defaults={"section": 1, "period": ""},
                )

                # Create instructors and associate with offering
                for name in instructor_names:
                    instructor, created = Instructor.objects.get_or_create(name=name)
                    if created:
                        instructor_count += 1

                    # Only add if not already associated
                    if instructor not in offering.instructors.all():
                        offering.instructors.add(instructor)
                        association_count += 1

        except Exception as e:
            print(f"  Error processing {course.course_code}: {str(e)}")

    print(f"Created {instructor_count} new instructors")
    print(f"Created {association_count} new instructor-course associations")
