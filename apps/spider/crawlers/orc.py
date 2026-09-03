import re
from urllib.parse import urljoin

from apps.spider.utils import retrieve_soup  # parse_number_and_subnumber,
from apps.web.models import Course, CourseOffering, Instructor
from lib.constants import CURRENT_TERM

BASE_URL = "https://gc.sjtu.edu.cn/"
ORC_BASE_URL = urljoin(BASE_URL, "/academics/courses/courses-by-number/")
# ORC_UNDERGRAD_SUFFIX = "Departments-Programs-Undergraduate"
# ORC_GRADUATE_SUFFIX = "Departments-Programs-Graduate"
COURSE_DETAIL_URL_PREFIX = (
    "https://gc.sjtu.edu.cn/academics/courses/courses-by-number/course-info/?id="
)
UNDERGRAD_URL = ORC_BASE_URL
INSTRUCTOR_TERM_REGEX = re.compile(r"^(?P<name>\w*)\s?(\((?P<term>\w*)\))?")

# SUPPLEMENT_URL = "http://dartmouth.smartcatalogiq.com/en/2016s/Supplement/Courses"

# COURSE_HEADING_CORRECTIONS = {
#     "COLT": {"7 First Year Seminars": "COLT 7 First Year Seminars"},
#     "GRK": {"GRK 1.02-3.02 Intensive Greek": "GRK 1.02 Intensive Greek"},
#     "INTS": {
#         "INTS INTS 17.04 Migration Stories": "INTS 17.04 Migration Stories",
#     },
#     "MALS": {
#         "MALS MALS 368 Seeing and Feeling in Early Modern Europe": (
#             "MALS 368 Seeing and Feeling in Early Modern Europe"
#         ),
#     },
#     "PSYC": {"$name": None},
#     "QBS": {
#         "Quantitative Biomedical Sciences 132-2 Molecular Markers in Human "
#         "Health Studies Lab": (
#             "QBS 132.02 Molecular Markers in Human Health Studies Lab"
#         ),
#     },
# }


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
    if not course_heading:
        return None
    split_course_heading = course_heading.split(" – ")
    if len(split_course_heading) < 2:
        return None

    course_code = split_course_heading[0]
    department = re.findall(r"^([A-Z]{2,4})\d+", course_code)[0]
    number = re.findall(r"^[A-Z]{2,4}(\d{3})", course_code)[0]
    course_title = split_course_heading[1]

    # The GC site wraps the labelled fields in nested divs (and lists topics
    # as plain <p>s rather than <li>s), so parse the flattened text stream of
    # the detail block instead of assuming direct children.
    content_sections = soup.find_all(class_="et_pb_text_inner")
    if len(content_sections) < 4:
        return None
    content_lines = [
        line.strip()
        for line in content_sections[3].get_text(separator="\n", strip=True).split("\n")
        if line.strip()
    ]

    section_markers = (
        "Instructors:",
        "Credits:",
        "Pre-requisites:",
        "Description:",
        "Course Topics:",
    )
    current_section = None
    section_lines = {}
    structure_recognized = False
    for line in content_lines:
        marker = next((m for m in section_markers if m in line), None)
        if marker is not None:
            current_section = marker
            structure_recognized = True
        elif current_section is not None:
            section_lines.setdefault(current_section, []).append(line)

    course_credits = 0
    if "Credits:" in section_lines:
        credits_match = re.findall(r"\d+", " ".join(section_lines["Credits:"]))
        if credits_match:
            course_credits = int(credits_match[0])
    pre_requisites = ""
    if "Pre-requisites:" in section_lines:
        pre_requisites = extract_prerequisites(
            "Pre-requisites: " + " ".join(section_lines["Pre-requisites:"])
        )
    description = " ".join(section_lines.get("Description:", [])).strip()
    course_topics = list(section_lines.get("Course Topics:", []))
    instructors = []
    for name_line in section_lines.get("Instructors:", []):
        instructors.extend(
            name.strip() for name in name_line.split(";") if name.strip()
        )

    return {
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
        # False when the page carried none of the known section markers; used
        # by import_department to skip updates so a broken crawl cannot wipe
        # existing course data. Stored records without this key default to
        # recognized for backward compatibility.
        "structure_recognized": structure_recognized,
    }


def import_department(department_data):
    for course_data in department_data:
        # Skip pages whose structure was not recognized: importing them would
        # overwrite stored course fields with empty values.
        if not course_data.get("structure_recognized", True):
            print(
                "Skipping {}: unrecognized page structure".format(
                    course_data.get("course_code", "<unknown>")
                )
            )
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
