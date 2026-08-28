import re
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup
from django.db import transaction

from apps.web.models import Course, CourseOffering, Instructor

OFFERINGS_URL = (
    "https://gc.sjtu.edu.cn/academics/courses/present-course-offerings/"
)
HEADING_RE = re.compile(
    r"Courses\s+Offered\s+in\s+(Spring|Summer|Fall)\s+(20\d{2})",
    re.IGNORECASE,
)
COURSE_CODE_RE = re.compile(
    r"^(?P<department>[A-Z]{2,5})(?P<number>\d{3,4})(?:J(?:-[A-Z0-9]+)?)?$"
)
INSTRUCTOR_SEPARATOR_RE = re.compile(r"\s*[,，;；]\s*")
TERM_CODES = {"spring": "SP", "summer": "SU", "fall": "FA"}
MIN_EXPECTED_OFFERINGS = 20


class GCOfferingsParseError(ValueError):
    pass


def crawl_gc_offerings(url=OFFERINGS_URL, timeout=30):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    offerings = parse_gc_offerings(response.text, source_url=response.url)
    if len(offerings) < MIN_EXPECTED_OFFERINGS:
        raise GCOfferingsParseError(
            f"only {len(offerings)} offerings were parsed; refusing partial crawl"
        )
    return offerings


def parse_gc_offerings(html, source_url=OFFERINGS_URL):
    soup = BeautifulSoup(html, "html.parser")
    heading = _find_offerings_heading(soup)
    term = _term_from_heading(heading.get_text(" ", strip=True))
    table = heading.find_next("table")
    if table is None:
        raise GCOfferingsParseError("course offerings table was not found")

    offerings = []
    section_counts = {}
    for values in _expand_table_rows(table, column_count=5):
        if not values or values[0].casefold() == "course code":
            continue
        current_course = _parse_course_cells(values[:4], source_url)
        instructor_text = values[4]
        course_code = current_course["course_code"]
        section_counts[course_code] = section_counts.get(course_code, 0) + 1
        offerings.append(
            {
                **current_course,
                "term": term,
                "section": section_counts[course_code],
                "instructors": _parse_instructors(instructor_text),
            }
        )

    if not offerings:
        raise GCOfferingsParseError("course offerings table contained no courses")
    return _coalesce_course_metadata(offerings)


def _coalesce_course_metadata(offerings):
    fields = (
        "course_title",
        "course_title_chn",
        "department",
        "number",
        "course_credits",
        "url",
    )
    by_code = {}
    for item in offerings:
        by_code.setdefault(item["course_code"], []).append(item)

    for course_code, items in by_code.items():
        for field in fields:
            populated = {
                item[field] for item in items if item[field] not in (None, "")
            }
            if len(populated) > 1:
                raise GCOfferingsParseError(
                    f"conflicting {field} values for {course_code}: "
                    f"{sorted(populated, key=str)!r}"
                )
            value = next(iter(populated), None)
            for item in items:
                item[field] = value

        crosslisted_codes = sorted(
            {
                code
                for item in items
                for code in item.get("crosslisted_codes", [])
            }
        )
        for item in items:
            item["crosslisted_codes"] = crosslisted_codes
    return offerings


def _expand_table_rows(table, column_count):
    """Expand HTML rowspans into complete logical rows."""
    carried = {}
    for row in table.find_all("tr"):
        values = [None] * column_count
        for column, (value, remaining) in list(carried.items()):
            values[column] = value
            if remaining == 1:
                del carried[column]
            else:
                carried[column] = (value, remaining - 1)

        for cell in row.find_all(["th", "td"], recursive=False):
            try:
                column = values.index(None)
            except ValueError as exc:
                raise GCOfferingsParseError("table row has too many cells") from exc
            value = cell.get_text(" ", strip=True)
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))
            if column + colspan > column_count:
                raise GCOfferingsParseError("table cell exceeds expected columns")
            for offset in range(colspan):
                target = column + offset
                if values[target] is not None:
                    raise GCOfferingsParseError("overlapping table cells")
                values[target] = value
                if rowspan > 1:
                    carried[target] = (value, rowspan - 1)

        if any(value is None for value in values):
            raise GCOfferingsParseError(f"incomplete table row: {values!r}")
        yield values


def _find_offerings_heading(soup):
    for heading in soup.find_all(["h1", "h2", "h3"]):
        if HEADING_RE.search(heading.get_text(" ", strip=True)):
            return heading
    raise GCOfferingsParseError("could not determine semester from page heading")


def _term_from_heading(heading):
    match = HEADING_RE.search(heading)
    if match is None:
        raise GCOfferingsParseError(f"invalid offerings heading: {heading!r}")
    season, year = match.groups()
    return f"{year[-2:]}{TERM_CODES[season.lower()]}"


def _parse_course_cells(values, source_url):
    raw_code, title_chn, title, credit_text = values
    codes = [code.strip().upper() for code in raw_code.split("/") if code.strip()]
    if not codes:
        raise GCOfferingsParseError("course code is empty")
    code_match = COURSE_CODE_RE.fullmatch(codes[0])
    if code_match is None:
        raise GCOfferingsParseError(f"unsupported course code: {raw_code!r}")

    credits = None
    if credit_text:
        try:
            credits = Decimal(credit_text)
        except InvalidOperation as exc:
            raise GCOfferingsParseError(f"invalid credits: {credit_text!r}") from exc
        if credits != credits.to_integral_value():
            raise GCOfferingsParseError(
                "fractional credits are not supported by the Course model: "
                f"{credit_text!r}"
            )
        credits = int(credits)

    return {
        "course_code": codes[0],
        "crosslisted_codes": codes[1:],
        "course_title": title,
        "course_title_chn": title_chn,
        "department": code_match.group("department"),
        "number": int(code_match.group("number")),
        "course_credits": credits,
        "url": source_url,
    }


def _parse_instructors(value):
    value = value.strip()
    if not value or value in {"-", "–", "—"}:
        return []
    return [name for name in INSTRUCTOR_SEPARATOR_RE.split(value) if name]


@transaction.atomic
def import_gc_offerings(offerings):
    if not offerings:
        raise ValueError("refusing to import an empty offerings list")
    terms = {item["term"] for item in offerings}
    if len(terms) != 1:
        raise ValueError("all offerings in one import must use the same term")
    term = terms.pop()
    imported_keys = set()

    for item in offerings:
        course, _ = Course.objects.update_or_create(
            course_code=item["course_code"],
            defaults={
                "course_title": item["course_title"],
                "department": item["department"],
                "number": item["number"],
                "course_credits": item["course_credits"],
                "url": item["url"],
            },
        )
        offering, _ = CourseOffering.objects.update_or_create(
            course=course,
            term=term,
            section=item["section"],
            defaults={"period": "", "limit": None},
        )
        instructors = [
            Instructor.objects.get_or_create(name=name)[0]
            for name in item["instructors"]
        ]
        offering.instructors.set(instructors)
        imported_keys.add((course.pk, item["section"]))

    stale_ids = [
        offering.pk
        for offering in CourseOffering.objects.filter(term=term)
        if (offering.course_id, offering.section) not in imported_keys
    ]
    CourseOffering.objects.filter(pk__in=stale_ids).delete()
    return len(imported_keys)
