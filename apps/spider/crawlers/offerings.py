import re
from urllib.parse import urljoin

from apps.spider.utils import retrieve_soup
from apps.web.models import Course, CourseOffering, Instructor

BASE_URL = "https://gc.sjtu.edu.cn/"
OFFERINGS_URL = urljoin(BASE_URL, "/academics/courses/present-course-offerings/")

TERM_CODES = {
    "spring": "S",
    "summer": "X",
    "fall": "F",
    "winter": "W",
}


def parse_offering_term(text):
    match = re.search(r"(Spring|Summer|Fall|Winter)\s+(\d{4})", text, re.I)
    if not match:
        return None

    season, year = match.groups()
    return f"{year[-2:]}{TERM_CODES[season.lower()]}"


def normalize_course_code(raw_course_code):
    match = re.match(
        r"^(?P<department>[A-Z]{2,4})(?P<number>\d{3,4}J?)",
        raw_course_code.strip(),
    )
    if not match:
        return None, None, None

    department = match.group("department")
    number_text = match.group("number").removesuffix("J")
    return f"{department}{match.group('number')}", department, int(number_text)


def parse_instructors(text):
    names = re.split(r";|,|，|\band\b", text)
    return [name.strip() for name in names if name.strip()]


def crawl_offerings(url=OFFERINGS_URL):
    soup = retrieve_soup(url)
    offering_data = []

    term_headings = [
        heading
        for heading in soup.find_all("h1")
        if "Courses Offered in" in heading.get_text(" ", strip=True)
    ]

    for heading in term_headings:
        term = parse_offering_term(heading.get_text(" ", strip=True))
        table = heading.find_next("table")
        if not term or table is None:
            continue

        current_record = None
        for row in table.find_all("tr")[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if not cells:
                continue

            if len(cells) >= 5:
                course_code, department, number = normalize_course_code(cells[0])
                if not course_code:
                    current_record = None
                    continue

                current_record = {
                    "term": term,
                    "course_code": course_code,
                    "department": department,
                    "number": number,
                    "course_title_zh": cells[1],
                    "course_title": cells[2],
                    "course_credits": int(cells[3]) if cells[3].isdigit() else 0,
                    "instructors": parse_instructors(cells[4]),
                }
                offering_data.append(current_record)
            elif len(cells) == 1 and current_record is not None:
                current_record["instructors"].extend(parse_instructors(cells[0]))

    return offering_data


def import_offerings(offering_data):
    for offering in offering_data:
        if not offering:
            continue

        course, created = Course.objects.get_or_create(
            course_code=offering["course_code"],
            defaults={
                "course_title": offering["course_title"][:100],
                "department": offering["department"],
                "number": offering["number"],
                "course_credits": offering["course_credits"],
            },
        )
        if not created:
            course.course_credits = offering["course_credits"]
            course.save(update_fields=["course_credits", "updated_at"])

        course_offering, _ = CourseOffering.objects.get_or_create(
            course=course,
            term=offering["term"],
            section=1,
            defaults={"period": "", "limit": None},
        )

        instructors = [
            Instructor.objects.get_or_create(name=name)[0]
            for name in offering.get("instructors", [])
        ]
        course_offering.instructors.set(instructors)
