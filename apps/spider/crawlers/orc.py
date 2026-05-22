import re
from urllib.parse import urljoin

from apps.spider.utils import retrieve_soup  # parse_number_and_subnumber,
from apps.web.models import Course, CourseOffering, Instructor
from lib.constants import CURRENT_TERM

BASE_URL = "https://gc.sjtu.edu.cn/"
ORC_BASE_URL = urljoin(BASE_URL, "/academics/courses/courses-by-number/")
COURSE_DETAIL_URL_PREFIX = (
    "https://gc.sjtu.edu.cn/academics/courses/courses-by-number/course-info/?id="
)
UNDERGRAD_URL = ORC_BASE_URL
INSTRUCTOR_TERM_REGEX = re.compile(r"^(?P<name>\w*)\s?(\((?P<term>\w*)\))?")


def crawl_program_urls():
    program_urls = set()  # Initialize to empty set
    for orc_url in [UNDERGRAD_URL]:
        program_urls.update(_get_department_urls_from_url(orc_url))
    return program_urls


def _get_department_urls_from_url(url):
    soup = retrieve_soup(url)
    linked_urls = [urljoin(BASE_URL, a["href"]) for a in soup.find_all("a", href=True)]
    return set(
        linked_url for linked_url in linked_urls if _is_department_url(linked_url)
    )


def _is_department_url(candidate_url):
    return candidate_url.startswith(COURSE_DETAIL_URL_PREFIX)


def _crawl_course_data(course_url):
    soup = retrieve_soup(course_url)
    course_heading_element = soup.find("h2")
    if course_heading_element is None:
        return None  # Return early if no h2 element found

    course_heading = course_heading_element.get_text()
    if course_heading:
        split_course_heading = course_heading.split(" – ")
        children = list(soup.find_all(class_="et_pb_text_inner")[3].children)

        raw_course_code = split_course_heading[0].strip()
        course_code_match = re.match(
            r"^(?P<department>[A-Z]{2,4})(?P<number>\d{3,4}J?)", raw_course_code
        )
        if not course_code_match:
            return None

        department = course_code_match.group("department")
        number_text = course_code_match.group("number").removesuffix("J")
        number = int(number_text)
        course_code = f"{department}{course_code_match.group('number')}"
        course_title = split_course_heading[1]

        course_credits = 0
        pre_requisites = ""
        description = ""
        course_topics = []
        instructors = []

        for i, child in enumerate(children):
            text = child.get_text(strip=True) if hasattr(child, "get_text") else ""
            if "Credits:" in text:
                credits_match = re.search(r"Credits:\s*(\d+)", text)
                course_credits = int(credits_match.group(1)) if credits_match else 0
            elif "Pre-requisites:" in text:
                pre_requisites = extract_prerequisites(text)
            elif "Description:" in text:
                description = (
                    children[i + 2].get_text(strip=True)
                    if i + 2 < len(children)
                    else ""
                )
                if description == "\n" or "Course Topics" in description:
                    description = ""
            elif "Course Topics:" in text:
                course_topics = (
                    [li.get_text(strip=True) for li in children[i + 2].find_all("li")]
                    if i + 2 < len(children)
                    else []
                )
            elif "Instructors:" in text:
                instructors_text = (
                    children[i + 2].get_text(strip=True)
                    if i + 2 < len(children)
                    else ""
                )
                instructors = [
                    name.strip() for name in instructors_text.split(";") if name.strip()
                ]

        result = {
            "course_code": course_code,
            "course_title": course_title,
            "department": department,
            "number": number,
            "course_credits": course_credits,
            "pre_requisites": pre_requisites,
            "description": description,
            "course_topics": course_topics,
            "instructors": instructors,
            "url": course_url,
        }
        return result


def import_department(department_data):
    for course_data in department_data:
        if not course_data:
            continue

        course, created = Course.objects.update_or_create(
            course_code=course_data["course_code"],
            defaults={
                "course_title": course_data["course_title"],
                "department": course_data["department"],
                "number": course_data["number"],
                "course_credits": course_data["course_credits"],
                "pre_requisites": course_data["pre_requisites"],
                "description": course_data["description"],
                "course_topics": course_data["course_topics"],
                "url": course_data["url"],
                # FIXME: invalid field source in course
                # "source": Course.SOURCES.ORC,
            },
        )

        # Handle instructors
        if "instructors" in course_data and course_data["instructors"]:
            for instructor_name in course_data["instructors"]:
                instructor, _ = Instructor.objects.get_or_create(name=instructor_name)
                # Create a course offering for the current term if it doesn't exist
                offering, _ = CourseOffering.objects.get_or_create(
                    course=course,
                    term=CURRENT_TERM,
                    defaults={"section": 1, "period": ""},
                )
                offering.instructors.add(instructor)


def extract_prerequisites(pre_requisites):
    result = pre_requisites

    result = result.replace("Pre-requisites:", "").strip()

    result = result.replace("Obtained Credit", "obtained_credit").strip()
    result = result.replace("Credits Submitted", "credits_submitted").strip()

    result = result.replace("&&", " && ").strip()
    result = result.replace("||", " || ").strip()

    return result
