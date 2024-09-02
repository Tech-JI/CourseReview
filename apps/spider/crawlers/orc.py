import re
from urllib.parse import urljoin

from apps.spider.utils import retrieve_soup  # parse_number_and_subnumber,
from apps.web.models import Course

# BASE_URL = "http://dartmouth.smartcatalogiq.com/"
BASE_URL = "https://www.ji.sjtu.edu.cn/"
ORC_BASE_URL = urljoin(BASE_URL, "/academics/courses/courses-by-number/")
# ORC_UNDERGRAD_SUFFIX = "Departments-Programs-Undergraduate"
# ORC_GRADUATE_SUFFIX = "Departments-Programs-Graduate"
COURSE_DETAIL_URL_PREFIX = (
    "https://www.ji.sjtu.edu.cn/academics/courses/courses-by-number/course-info/?id="
)
# GRADUATE_URL = urljoin(ORC_BASE_URL, ORC_GRADUATE_SUFFIX)
UNDERGRAD_URL = ORC_BASE_URL
INSTRUCTOR_TERM_REGEX = re.compile("^(?P<name>\w*)\s?(\((?P<term>\w*)\))?")

SUPPLEMENT_URL = "http://dartmouth.smartcatalogiq.com/en/2016s/Supplement/Courses"

COURSE_HEADING_CORRECTIONS = {
    "COLT": {"7 First Year Seminars": "COLT 7 First Year Seminars"},
    "GRK": {"GRK 1.02-3.02 Intensive Greek": "GRK 1.02 Intensive Greek"},
    "INTS": {
        "INTS INTS 17.04 Migration Stories": "INTS 17.04 Migration Stories",
    },
    "MALS": {
        "MALS MALS 368 Seeing and Feeling in Early Modern Europe": (
            "MALS 368 Seeing and Feeling in Early Modern Europe"
        ),
    },
    "PSYC": {"$name": None},
    "QBS": {
        "Quantitative Biomedical Sciences 132-2 Molecular Markers in Human "
        "Health Studies Lab": (
            "QBS 132.02 Molecular Markers in Human Health Studies Lab"
        ),
    },
}


def crawl_program_urls():
    # programs = set()
    # for orc_url in [UNDERGRAD_URL, GRADUATE_URL]:
    for orc_url in [UNDERGRAD_URL]:
        program_urls = _get_department_urls_from_url(orc_url)
        # for department_url in department_urls:
        #     programs |= _get_program_urls_from_department_url(department_url)
    return program_urls


def _get_department_urls_from_url(url):
    soup = retrieve_soup(url)
    linked_urls = [urljoin(BASE_URL, a["href"]) for a in soup.find_all("a", href=True)]
    return set(
        linked_url for linked_url in linked_urls if _is_department_url(linked_url)
    )


def _is_department_url(candidate_url):
    return candidate_url.startswith(COURSE_DETAIL_URL_PREFIX)


# def _get_program_urls_from_department_url(url):
#     soup = retrieve_soup(url)
#     linked_urls = [
#         urljoin(BASE_URL, a["href"]) for a in soup.find_all("a", href=True)
#     ]
#     program_urls = set()
#     for potential_program_url in linked_urls:
#         if _is_course_url(potential_program_url):
#             potential_program_url = "/".join(
#                 potential_program_url.split("/")[:-1])
#         if _is_program_url(potential_program_url, url):
#             program_urls.add(potential_program_url)
#     return program_urls

# def _is_program_url(candidate_url, department_url):
#     top_directory_words = candidate_url.split("/")[-1].split("-")
#     potential_department_name = top_directory_words[0]
#     return (candidate_url.startswith(ORC_BASE_URL)
#             and all(word.isalpha() for word in top_directory_words)
#             and len(potential_department_name) in [3, 4]
#             and potential_department_name.isupper()
#             and not _is_course_url(candidate_url))

# def crawl_courses_from_program_page_url(url):
#     # soup = retrieve_soup(url)
#     # course_urls = [
#     #     urljoin(BASE_URL, a["href"]) for a in soup.find_all("a", href=True)
#     # ]
#     # course_urls = sorted(set(url for url in linked_urls
#     #                          if _is_course_url(url)))
#     return filter(
#         None,
#         [
#             _crawl_course_data(url)
#             # for course_url in course_urls
#         ],
#     )

# def _is_course_url(candidate_url):
#     potential_course_data = candidate_url.split("/")[-1].split("-")
#     return (len(potential_course_data) in (2, 3)
#             and len(potential_course_data[0]) in (3, 4)
#             and potential_course_data[0].isupper()
#             and all(potential_number.isdigit()
#                     for potential_number in potential_course_data[1:]))


def _crawl_course_data(course_url):
    soup = retrieve_soup(course_url)
    course_heading = soup.find("h2").get_text()
    # course_heading = COURSE_HEADING_CORRECTIONS.get(program_code, {}).get(
    #     course_heading, course_heading)
    if course_heading:
        # split_course_heading = course_heading.split()
        # department = split_course_heading[0]
        # number, subnumber = parse_number_and_subnumber(split_course_heading[1])
        # course_title = " ".join(split_course_heading[2:])
        # description = soup.find(class_="desc").get_text(strip=True)
        # return {
        #     "department": department,
        #     "description": description,
        #     "number": number,
        #     "subnumber": subnumber,
        #     "title": course_title,
        #     "url": course_url,
        # }
        split_course_heading = course_heading.split(" – ")
        children = list(soup.find_all(class_="et_pb_text_inner")[3].children)

        course_code = split_course_heading[0]
        department = re.findall(r"^([A-Z]{2,4})\d+", course_code)[0]
        number = re.findall(r"^[A-Z]{2,4}(\d{3})", course_code)[0]
        course_title = split_course_heading[1]

        course_credits = 0
        pre_requisites = ""
        description = ""
        course_topics = []

        for i, child in enumerate(children):
            text = child.get_text(strip=True) if hasattr(child, "get_text") else ""
            if "Credits" in text:
                course_credits = int(re.findall(r"\d+", text)[0])
            elif "Pre-requisites" in text:
                pre_requisites = extract_prerequisites(text)
            elif "Description" in text:
                description = (
                    children[i + 2].get_text(strip=True)
                    if i + 2 < len(children)
                    else ""
                )
                if description == "\n" or "Course Topics" in description:
                    description = ""
            elif "Course Topics" in text:
                course_topics = (
                    [li.get_text(strip=True) for li in children[i + 2].find_all("li")]
                    if i + 2 < len(children)
                    else []
                )

        result = {
            "course_code": course_code,
            "course_title": course_title,
            "department": department,
            "number": number,
            "course_credits": course_credits,
            "pre_requisites": pre_requisites,
            "description": description,
            "course_topics": course_topics,
            "url": course_url,
        }
        # print("result: ", result)
        return result
        # return {
        #     "course_code": "QWER1234J",
        #     "course_title": "Test Course",
        #     "department": "QWER",
        #     "number": 1234,
        #     "course_credits": 4,
        #     "pre_requisites": None,
        #     "description": "This is a test course",
        #     "course_topics": ["Test Topic"],
        #     "url": course_url,
        # }


# def get_education_level_code(url):
#     if url.startswith(UNDERGRAD_URL) or url == SUPPLEMENT_URL:
#         return "ug"
#     else:
#         # assert url.startswith(GRADUATE_URL)
#         return "gr"


def import_department(department_data):
    for course_data in department_data:
        Course.objects.update_or_create(
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


def extract_prerequisites(pre_requisites):
    result = pre_requisites

    result = result.replace("Pre-requisites:", "").strip()

    result = result.replace("Obtained Credit", "Obtained_Credit").strip()
    result = result.replace("Credits Submitted", "Credits_Submitted").strip()

    result = result.replace("&&", " && ").strip()
    result = result.replace("||", " || ").strip()

    return result
