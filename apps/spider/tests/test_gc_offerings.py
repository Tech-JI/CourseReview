import pytest
from django.conf import settings

from apps.spider.crawlers.gc_offerings import (
    GCOfferingsParseError,
    import_gc_offerings,
    parse_gc_offerings,
)
from apps.web.models import Course, CourseOffering


SAMPLE_HTML = """
<html><body>
  <h1>Courses for the Upcoming Semester</h1>
  <h1>Courses Offered in Summer 2026</h1>
  <table><tbody>
    <tr><td>Course Code</td><td>Course Title -CHN</td>
        <td>Course Title -ENG</td><td>Crs</td><td>Instructor(s)</td></tr>
    <tr><td rowspan="2">PHYS1500J</td><td rowspan="2">普通物理</td>
        <td rowspan="2">Physics I</td><td rowspan="2">4</td>
        <td>Richard Grumitt</td></tr>
    <tr><td>Mesli Abdelmadjid</td></tr>
    <tr><td>PHYS1410J</td><td>物理实验</td><td>Physics Lab I</td><td>1</td>
        <td>Yuxing Wang，Qianli Chen</td></tr>
    <tr><td>MSE3350J/VK335</td><td>材料工程</td><td>Materials</td><td>4</td>
        <td>–</td></tr>
    <tr><td>ME4500J</td><td>设计制造</td><td>Design</td><td>4</td>
        <td rowspan="2">Teacher A, Teacher B</td></tr>
    <tr><td>ECE4500J</td><td>系统设计</td><td>Systems Design</td><td>4</td></tr>
  </tbody></table>
</body></html>
"""


def test_parse_gc_offerings_handles_rowspan_instructors_and_crosslists():
    rows = parse_gc_offerings(SAMPLE_HTML)

    assert len(rows) == 6
    assert rows[0]["term"] == "26SU"
    assert rows[0]["course_code"] == "PHYS1500J"
    assert rows[0]["section"] == 1
    assert rows[0]["instructors"] == ["Richard Grumitt"]
    assert rows[1]["course_code"] == "PHYS1500J"
    assert rows[1]["section"] == 2
    assert rows[1]["instructors"] == ["Mesli Abdelmadjid"]
    assert rows[2]["instructors"] == ["Yuxing Wang", "Qianli Chen"]
    assert rows[3]["course_code"] == "MSE3350J"
    assert rows[3]["crosslisted_codes"] == ["VK335"]
    assert rows[3]["instructors"] == []
    assert rows[4]["instructors"] == ["Teacher A", "Teacher B"]
    assert rows[5]["course_code"] == "ECE4500J"
    assert rows[5]["instructors"] == ["Teacher A", "Teacher B"]


def test_parse_gc_offerings_rejects_a_missing_table():
    with pytest.raises(GCOfferingsParseError, match="table was not found"):
        parse_gc_offerings("<h1>Courses Offered in Summer 2026</h1>")


def test_parse_gc_offerings_fills_missing_credits_from_another_section():
    html = """
    <h1>Courses Offered in Summer 2026</h1>
    <table>
      <tr><td>Course Code</td><td>Course Title -CHN</td>
          <td>Course Title -ENG</td><td>Crs</td><td>Instructor(s)</td></tr>
      <tr><td>TC4960J</td><td>科技写作</td><td>Technical Communication</td>
          <td></td><td>Teacher A</td></tr>
      <tr><td>TC4960J</td><td>科技写作</td><td>Technical Communication</td>
          <td>2</td><td>Teacher B</td></tr>
    </table>
    """

    rows = parse_gc_offerings(html)

    assert [row["course_credits"] for row in rows] == [2, 2]


@pytest.mark.skipif(
    "postgresql" not in settings.DATABASES["default"]["ENGINE"],
    reason="project migrations use PostgreSQL-only ArrayField columns",
)
@pytest.mark.django_db
def test_import_gc_offerings_syncs_courses_sections_and_instructors():
    rows = parse_gc_offerings(SAMPLE_HTML)
    stale_course = Course.objects.create(
        course_code="OLD1000J", course_title="Old", department="OLD", number=1000
    )
    CourseOffering.objects.create(
        course=stale_course, term="26SU", section=1, period=""
    )

    assert import_gc_offerings(rows) == 4

    physics = Course.objects.get(course_code="PHYS1500J")
    sections = list(
        physics.courseoffering_set.filter(term="26SU").order_by("section")
    )
    assert len(sections) == 2
    assert list(sections[0].instructors.values_list("name", flat=True)) == [
        "Richard Grumitt"
    ]
    assert list(sections[1].instructors.values_list("name", flat=True)) == [
        "Mesli Abdelmadjid"
    ]
    assert not CourseOffering.objects.filter(
        course=stale_course, term="26SU"
    ).exists()
