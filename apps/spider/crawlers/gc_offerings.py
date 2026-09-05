import re
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup
from django.db import models, transaction

from apps.web.models import Course, CourseOffering, Instructor

OFFERINGS_URL = "https://gc.sjtu.edu.cn/academics/courses/present-course-offerings/"
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

# ---------------------------------------------------------------------------
# Instructor name canonicalization
#
# The GC page itself is inconsistent: the same person appears under different
# spellings across terms (case, hyphens, middle names, term annotations like
# "(Fall)", CJK annotations like "闫旭", or even full-name/short-name
# alternation). Importing each cell verbatim with get_or_create(name) silently
# forks one teacher into several Instructor rows every time the page rotates.
# The pure-string cleaning/matching helpers live in lib.name_normalization
# (shared with the review API); the functions here resolve against the live
# Instructor table.
# ---------------------------------------------------------------------------

from lib.name_normalization import (  # noqa: E402
    INSTRUCTOR_SPLITS,
    JUNK_INSTRUCTOR_NAMES,
    best_name_match,
    clean_instructor_name,
)


def _best_instructor_match(clean_name, existing):
    """Find the Instructor row a cleaned name should map to.

    Candidates are ordered by usage (most offerings first) so ties resolve to
    the most-used spelling as canonical. Returns None when nothing plausibly
    matches.
    """
    ranked = sorted(
        existing,
        key=lambda r: (-_offering_count(r), r.id),
    )
    matched = best_name_match(clean_name, [r.name for r in ranked])
    if matched is None:
        return None
    return next((r for r in ranked if r.name == matched), None)


def _offering_count(row):
    """Offering count for tie-breaking, honoring a prefetched annotation."""
    count = getattr(row, "_offering_count", None)
    if count is not None:
        return count
    return row.courseoffering_set.count()


def resolve_instructor(clean_name, existing=None):
    """Return the Instructor row for a cleaned name, reusing existing rows
    across spelling variants. Creates a new row only when no existing
    instructor plausibly matches."""
    existing = (
        list(existing) if existing is not None else list(Instructor.objects.all())
    )
    match = _best_instructor_match(clean_name, existing)
    if match is not None:
        return match
    instructor, _ = Instructor.objects.get_or_create(name=clean_name)
    return instructor


def expand_instructor_names(raw_names, existing):
    """Resolve raw GC cell text to Instructor rows, self-defensively.

    Applies cleaning, junk filtering, and curated multi-person splits so the
    importer behaves correctly even when handed payloads stored before the
    canonicalization logic existed. Returns a deduped list of Instructor rows.
    """
    resolved = []
    for raw in raw_names:
        cleaned = clean_instructor_name(raw)
        if not cleaned or cleaned.lower() in JUNK_INSTRUCTOR_NAMES:
            continue
        for name in INSTRUCTOR_SPLITS.get(cleaned, [cleaned]):
            inst = resolve_instructor(name, existing)
            if all(row.id != inst.id for row in existing):
                existing.append(inst)
            if not any(row.id == inst.id for row in resolved):
                resolved.append(inst)
    return resolved


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
    offerings = []
    for heading in _find_offerings_headings(soup):
        term = _term_from_heading(heading.get_text(" ", strip=True))
        table = heading.find_next("table")
        if table is None:
            raise GCOfferingsParseError("course offerings table was not found")

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
        key = (item["term"], item["course_code"])
        by_code.setdefault(key, []).append(item)

    for (_, course_code), items in by_code.items():
        for field in fields:
            populated = {item[field] for item in items if item[field] not in (None, "")}
            if len(populated) > 1:
                raise GCOfferingsParseError(
                    f"conflicting {field} values for {course_code}: "
                    f"{sorted(populated, key=str)!r}"
                )
            value = next(iter(populated), None)
            for item in items:
                item[field] = value

        crosslisted_codes = sorted(
            {code for item in items for code in item.get("crosslisted_codes", [])}
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


def _find_offerings_headings(soup):
    headings = [
        heading
        for heading in soup.find_all(["h1", "h2", "h3"])
        if HEADING_RE.search(heading.get_text(" ", strip=True))
    ]
    if not headings:
        raise GCOfferingsParseError("could not determine semester from page heading")
    return headings


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
    names = []
    for raw in INSTRUCTOR_SEPARATOR_RE.split(value or ""):
        cleaned = clean_instructor_name(raw)
        if not cleaned or cleaned.lower() in JUNK_INSTRUCTOR_NAMES:
            continue
        # Expand cells that cram several instructors together (curated).
        names.extend(INSTRUCTOR_SPLITS.get(cleaned, [cleaned]))
    return names


@transaction.atomic
def import_gc_courses(offerings):
    if not offerings:
        raise ValueError("refusing to import an empty course list")
    courses_by_code = {}
    existing = list(
        Instructor.objects.annotate(_offering_count=models.Count("courseoffering"))
    )

    for item in offerings:
        course = courses_by_code.get(item["course_code"])
        if course is None:
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
            courses_by_code[item["course_code"]] = course

        instructors = expand_instructor_names(item["instructors"], existing)
        # Sections are numbered by row order within the GC page table, not by
        # the registrar's section numbers (the page has no such column).
        offering, _ = CourseOffering.objects.get_or_create(
            course=course,
            term=item["term"],
            section=item["section"],
            defaults={"period": ""},
        )
        offering.instructors.set(instructors)

    return len(courses_by_code)
