import re
import urllib.parse
import logging

import json
import requests
import time
from collections import defaultdict

from apps.web.models import Course, CourseOffering, Instructor
from lib.constants import CURRENT_TERM

# API endpoints
BASE_URL = "https://coursesel.umji.sjtu.edu.cn"
COURSE_DETAIL_URL_PREFIX = urllib.parse.urljoin(BASE_URL, "/course/")

# Legacy compatibility
ORC_BASE_URL = BASE_URL
UNDERGRAD_URL = BASE_URL

# Set up logger
logger = logging.getLogger(__name__)


class CourseSelCrawler:
    """
    JI SJTU Course Selection System Crawler

    Crawls course data from three APIs:
    1. Lesson tasks API: course offerings and basic info
    2. Course catalog API: detailed descriptions
    3. Prerequisites API: prerequisite rules
    """

    def __init__(self, jsessionid=None):
        """Initialize crawler with session and authentication"""
        self.session = requests.Session()
        self.jsessionid = jsessionid
        self._initialized = False

        logger.info("Crawler created (not yet initialized)")

    def _ensure_initialized(self):
        """Ensure crawler is properly initialized with authentication"""
        if self._initialized:
            return

        if not self.jsessionid:
            print("Please enter your JSESSIONID cookie:")
            print("(Found in browser dev tools under Network or Application tabs)")
            self.jsessionid = input("JSESSIONID: ").strip()

        if not self.jsessionid:
            raise ValueError("JSESSIONID cannot be empty")

        cookies = {"JSESSIONID": self.jsessionid}
        self.session.cookies.update(cookies)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": BASE_URL,
            "X-Requested-With": "XMLHttpRequest",
        }
        self.session.headers.update(headers)

        self._initialized = True
        logger.info("Crawler initialized successfully!")

    def get_all_courses(self):
        """
        Get all course data from multiple APIs

        Returns:
            list: Course data with prerequisites, descriptions, and instructors
        """
        courses_data = self._get_lesson_tasks()
        course_details = self._get_course_catalog()
        prerequisites = self._get_prerequisites()

        return self._integrate_course_data(courses_data, course_details, prerequisites)

    def _get_current_elect_turn_id(self):
        """Get current election turn ID dynamically"""
        url = f"{BASE_URL}/tpm/findStudentElectTurns_ElectTurn.action"

        try:
            response = self.session.get(url, params={"_t": int(time.time() * 1000)})
            response.raise_for_status()
            data = response.json()

            if data and isinstance(data, list) and len(data) > 0:
                # Get the first (current) election turn
                current_turn = data[0]
                elect_turn_id = current_turn.get("electTurnId")
                if elect_turn_id:
                    logger.debug(f"Found current electTurnId: {elect_turn_id}")
                    return elect_turn_id

            logger.warning("Could not find current electTurnId, using fallback")
            return "1A5D7E45-4C23-4ED4-A3C2-90C45BE2E1E4"  # Fallback
        except Exception as e:
            logger.error(f"Error getting electTurnId: {e}, using fallback")
            return "1A5D7E45-4C23-4ED4-A3C2-90C45BE2E1E4"  # Fallback

    def _get_lesson_tasks(self):
        """Get lesson task data from course selection API"""
        url = f"{BASE_URL}/tpm/findLessonTasksPreview_ElectTurn.action"

        # Get current election turn ID dynamically
        elect_turn_id = self._get_current_elect_turn_id()

        json_params = {
            "isToTheTime": True,
            "electTurnId": elect_turn_id,
            "loadCourseGroup": True,
            "loadElectTurn": True,
            "loadCourseType": True,
            "loadCourseTypeCredit": True,
            "loadElectTurnResult": True,
            "loadStudentLessonTask": True,
            "loadPrerequisiteCourse": True,
            "loadLessonCalendarWeek": True,
            "loadLessonCalendarConflict": True,
            "loadTermCredit": True,
            "loadLessonTask": True,
            "loadDropApprove": True,
            "loadElectApprove": True,
        }

        json_string = json.dumps(json_params, separators=(",", ":"))
        encoded_json = urllib.parse.quote(json_string)
        full_url = f"{url}?jsonString={encoded_json}"

        try:
            response = self.session.get(full_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and "data" in data and "lessonTasks" in data["data"]:
                return data["data"]["lessonTasks"]
            return []
        except Exception:
            return []

    def _get_course_catalog(self):
        """Get course catalog data with detailed descriptions"""
        url = f"{BASE_URL}/jdji/tpm/findOwnCollegeCourse_JiCourse.action"

        try:
            response = self.session.post(url, json={})
            response.raise_for_status()
            data = response.json()

            if data.get("success") and "data" in data:
                if isinstance(data["data"], list):
                    courses = data["data"]
                else:
                    return {}
                return {course.get("courseId"): course for course in courses}
            return {}
        except Exception:
            return {}

    def _get_prerequisites(self):
        """Get prerequisite data with course requirements and logic"""
        url = f"{BASE_URL}/tpm/findAll_PrerequisiteCourse.action"

        try:
            response = self.session.post(url, params={"_t": int(time.time() * 1000)})
            response.raise_for_status()
            data = response.json()

            logger.debug(f"Prerequisites API response: success={data.get('success')}")
            logger.debug(
                f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}"
            )

            if data.get("success") and "data" in data:
                raw_prereqs = data["data"]
                logger.debug(f"Raw prerequisites data: {len(raw_prereqs)} items")

                if raw_prereqs and len(raw_prereqs) > 0:
                    logger.debug(f"First prerequisite item: {raw_prereqs[0]}")

                prereqs = defaultdict(list)
                for item in raw_prereqs:
                    course_id = item.get("courseId")
                    if course_id:
                        prereqs[course_id].append(item)

                logger.debug(
                    f"Grouped prerequisites: {len(prereqs)} course IDs have prereqs"
                )
                return prereqs
            else:
                logger.warning("Prerequisites API failed or no data")
                return {}
        except Exception as e:
            logger.error(f"Prerequisites API error: {str(e)}")
            return {}

    def _integrate_course_data(self, courses_data, course_details, prerequisites):
        """Integrate course data from multiple sources"""
        logger.info(
            f"Starting integration with {len(courses_data)} courses, {len(prerequisites)} prereq groups"
        )

        courses_by_code = defaultdict(list)
        for course in courses_data:
            course_code = course.get("courseCode")
            if course_code:
                courses_by_code[course_code].append(course)

        integrated_courses = []
        courses_with_prereqs = 0

        for course_code, course_list in courses_by_code.items():
            merged = self._merge_course_sections(course_list)
            if not merged:
                continue

            course_id = merged.get("courseId")
            catalog_info = course_details.get(course_id, {})
            prereq_info = prerequisites.get(course_id, [])

            if prereq_info:
                courses_with_prereqs += 1
                logger.debug(
                    f"Course {course_code} (ID: {course_id}) has {len(prereq_info)} prereqs"
                )

            course_data = self._build_course_record(
                course_code, merged, catalog_info, prereq_info
            )

            if course_data:
                integrated_courses.append(course_data)

        logger.info(
            f"Integration complete: {courses_with_prereqs} courses have prerequisites"
        )
        return integrated_courses

    def _merge_course_sections(self, course_list):
        """Merge sections of the same course"""
        if not course_list:
            return {}

        merged = course_list[0].copy()
        all_instructors = set()

        for course in course_list:
            teachers = course.get("lessonTaskTeam", "")
            if teachers:
                for teacher in re.split(r"[,;，；、]", teachers):
                    if teacher.strip():
                        all_instructors.add(teacher.strip())

        merged["all_instructors"] = list(all_instructors)
        return merged

    def _build_course_record(self, course_code, main_data, catalog_data, prereq_data):
        """Build standardized course record"""
        course_title = self._extract_course_title(main_data, catalog_data)
        if not course_title:
            return None

        department, number = self._parse_course_code(course_code)
        course_credits = self._extract_course_credits(main_data, catalog_data)
        prerequisites = self._build_prerequisites_string(course_code, prereq_data)
        description = self._extract_description(main_data, catalog_data)
        instructors = self._extract_instructors(main_data, catalog_data)
        course_url = self._build_course_url(main_data)

        return {
            "course_code": course_code,
            "course_title": course_title,
            "department": department,
            "number": number,
            "course_credits": course_credits,
            "pre_requisites": prerequisites,
            "description": description,
            "course_topics": [],
            "instructors": instructors,
            "url": course_url,
        }

    def _extract_course_title(self, main_data, catalog_data):
        """Extract course title (prefer English name)"""
        return (
            main_data.get("courseNameEn", "")
            or main_data.get("courseName", "")
            or catalog_data.get("courseNameEn", "")
            or catalog_data.get("courseName", "")
        ).strip()

    def _parse_course_code(self, course_code):
        department = ""
        number = 0

        if course_code:
            # Match DEPT####J? (J is optional)
            match = re.match(r"^([A-Z]{2,4})(\d{4})J?$", course_code)
            if match:
                department = match.group(1)
                number = int(match.group(2))

        return department, number

    def _extract_course_credits(self, main_data, catalog_data):
        """Extract course credits"""
        course_credits = main_data.get("totalCredit", 0) or catalog_data.get(
            "credit", 0
        )

        if isinstance(course_credits, str):
            try:
                course_credits = int(float(course_credits))
            except (ValueError, TypeError):
                course_credits = 0

        return course_credits

    def _build_prerequisites_string(self, course_code, prereq_data):
        """Build prerequisites string from API data"""
        if not prereq_data:
            return ""

        logger.debug(
            f"Building prerequisites for {course_code}, prereq_data has {len(prereq_data)} items"
        )

        prereq_codes = []
        for item in prereq_data:
            rule_desc = item.get("prerequisiteRuleDesc", "")
            logger.debug(f"Processing prerequisite rule: {rule_desc}")

            if rule_desc:
                prereq_codes.append(rule_desc)

        if prereq_codes:
            prerequisites = " || ".join(prereq_codes)
            logger.debug(f"Final prerequisites for {course_code}: {prerequisites}")
            return prerequisites

        return ""

    def _extract_description(self, main_data, catalog_data):
        """Extract course description"""
        return (
            main_data.get("description", "")
            or catalog_data.get("description", "")
            or main_data.get("memo", "")
            or catalog_data.get("memo", "")
        ).strip()

    def _extract_instructors(self, main_data, catalog_data):
        """Extract and merge instructor information"""
        instructors = main_data.get("all_instructors", [])
        teacher_name = catalog_data.get("teacherName", "")

        if teacher_name:
            for teacher in re.split(r"[,;，；、]", teacher_name):
                if teacher.strip() and teacher.strip() not in instructors:
                    instructors.append(teacher.strip())

        return instructors

    def _build_course_url(self, main_data):
        """Build course detail page URL"""
        course_id = main_data.get("courseId")
        return f"{COURSE_DETAIL_URL_PREFIX}{course_id}" if course_id else ""


# Legacy compatibility functions
_crawler = None


def _get_crawler():
    """Get crawler instance (singleton pattern)"""
    global _crawler
    if _crawler is None:
        _crawler = CourseSelCrawler()
    return _crawler


def crawl_program_urls():
    """Get all course URLs (legacy interface)"""
    crawler = _get_crawler()
    courses = crawler.get_all_courses()

    course_urls = []
    for course in courses:
        if course.get("url"):
            course_urls.append(course["url"])

    if not hasattr(crawl_program_urls, "_course_data_cache"):
        crawl_program_urls._course_data_cache = {}

    for course in courses:
        if course.get("url"):
            crawl_program_urls._course_data_cache[course["url"]] = course

    return course_urls


def _get_department_urls_from_url(_):
    """Legacy function: get department course URLs"""
    return crawl_program_urls()


def _is_department_url(candidate_url):
    """Check if URL is a valid course detail URL"""
    return candidate_url.startswith(COURSE_DETAIL_URL_PREFIX)


def _crawl_course_data(course_url):
    """Crawl single course data (legacy interface)"""
    if hasattr(crawl_program_urls, "_course_data_cache"):
        course_data = crawl_program_urls._course_data_cache.get(course_url)
        if course_data:
            return course_data

    return {}


def import_department(department_data):
    """Import course data to database"""
    for course_data in department_data:
        course, _ = Course.objects.update_or_create(
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
            },
        )

        if "instructors" in course_data and course_data["instructors"]:
            for instructor_name in course_data["instructors"]:
                instructor, _ = Instructor.objects.get_or_create(name=instructor_name)

                offering, _ = CourseOffering.objects.get_or_create(
                    course=course,
                    term=CURRENT_TERM,
                    defaults={"section": 1, "period": ""},
                )
                offering.instructors.add(instructor)


def extract_prerequisites(pre_requisites):
    """Process prerequisite string format (legacy function)"""
    result = pre_requisites

    result = result.replace("Pre-requisites:", "").strip()
    result = result.replace("Obtained Credit", "obtained_credit").strip()
    result = result.replace("Credits Submitted", "credits_submitted").strip()
    result = result.replace("&&", " && ").strip()
    result = result.replace("||", " || ").strip()

    return result
