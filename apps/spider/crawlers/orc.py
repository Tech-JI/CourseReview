import re
import urllib.parse
import logging
import asyncio
import aiohttp
import json
from datetime import datetime

import requests
import time
from collections import defaultdict
from urllib.parse import urljoin

from apps.spider.utils import retrieve_soup
from apps.spider.manager import CourseDataCache
from apps.web.models import Course, CourseOffering, Instructor
from lib.constants import CURRENT_TERM

# Set up logger
logger = logging.getLogger(__name__)


class CrawlerConfig:
    """
    Configuration class for all crawler components

    Contains URLs, timeouts, limits, and other configurable parameters
    used across different crawler classes.
    """

    # Course Selection System API Configuration
    COURSESEL_BASE_URL = "https://coursesel.umji.sjtu.edu.cn"
    COURSESEL_APIS = ["lesson_tasks", "course_catalog", "prerequisites"]

    # Official Website Configuration
    OFFICIAL_BASE_URL = "https://www.ji.sjtu.edu.cn/"
    OFFICIAL_ORC_BASE_URL = (
        "https://www.ji.sjtu.edu.cn/academics/courses/courses-by-number/"
    )
    OFFICIAL_COURSE_DETAIL_URL_PREFIX = "https://www.ji.sjtu.edu.cn/academics/courses/courses-by-number/course-info/?id="

    # Request Configuration
    REQUEST_TIMEOUT = 30
    CONNECT_TIMEOUT = 3
    READ_TIMEOUT = 10
    MAX_RETRIES = 2
    RETRY_DELAY = 1.0

    # Concurrency Configuration
    MAX_CONNECTIONS = 50
    CONNECTIONS_PER_HOST = 25
    CONCURRENT_REQUESTS = 20
    READ_BUFFER_SIZE = 32768

    # DNS and Connection Configuration
    DNS_CACHE_TTL = 600
    KEEPALIVE_TIMEOUT = 30

    # Data Processing Configuration
    DEFAULT_BATCH_SIZE = 100
    MAX_COURSE_TOPICS = 10

    # Headers Configuration
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

    # Translation Configuration
    CHINESE_TO_ENGLISH_TRANSLATIONS = {
        "已获学分": "Obtained Credit",
        "已提交学分": "Credits Submitted",
        "学分": "Credit",
        "先修": "Prerequisite",
        "课程": "Course",
        "或": "or",
        "且": "and",
        "以上": "above",
        "学期": "Semester",
        "年级": "Grade",
    }


# Legacy constants for backward compatibility
BASE_URL = CrawlerConfig.COURSESEL_BASE_URL
COURSE_DETAIL_URL_PREFIX = urllib.parse.urljoin(BASE_URL, "/course/")
OFFICIAL_BASE_URL = CrawlerConfig.OFFICIAL_BASE_URL
OFFICIAL_ORC_BASE_URL = CrawlerConfig.OFFICIAL_ORC_BASE_URL
OFFICIAL_COURSE_DETAIL_URL_PREFIX = CrawlerConfig.OFFICIAL_COURSE_DETAIL_URL_PREFIX
OFFICIAL_UNDERGRAD_URL = OFFICIAL_ORC_BASE_URL


class CourseSelAPICrawler:
    """
    Course Selection System API Crawler

    Handles authentication and data retrieval from the JI SJTU course selection system.
    Supports three main APIs: lesson tasks, course catalog, and prerequisites.
    """

    def __init__(self, jsessionid=None):
        """
        Initialize the Course Selection API crawler

        Args:
            jsessionid (str, optional): Session ID for authentication
        """
        self.session = requests.Session()
        self.jsessionid = jsessionid
        self._initialized = False

        logger.info("CourseSelAPICrawler created")

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

        headers = CrawlerConfig.DEFAULT_HEADERS.copy()
        headers.update(
            {
                "Referer": CrawlerConfig.COURSESEL_BASE_URL,
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        self.session.headers.update(headers)

        self._initialized = True
        logger.info("CourseSelAPICrawler initialized successfully")

    def set_session_id(self, jsessionid):
        """
        Set or update the session ID

        Args:
            jsessionid (str): New session ID
        """
        self.jsessionid = jsessionid
        self._initialized = False
        self._ensure_initialized()

    def crawl_all_apis(self, apis=None):
        """
        Crawl data from all or specified APIs

        Args:
            apis (list, optional): List of API names to crawl.
                                 If None, crawl all APIs.

        Returns:
            dict: Dictionary containing data from each API
        """
        if apis is None:
            apis = CrawlerConfig.COURSESEL_APIS

        self._ensure_initialized()

        results = {}

        if "lesson_tasks" in apis:
            results["lesson_tasks"] = self.crawl_lesson_tasks()

        if "course_catalog" in apis:
            results["course_catalog"] = self.crawl_course_catalog()

        if "prerequisites" in apis:
            results["prerequisites"] = self.crawl_prerequisites()

        return results

    def crawl_lesson_tasks(self):
        """
        Crawl lesson task data from the course selection API

        Returns:
            list: List of lesson task records
        """
        self._ensure_initialized()

        url = f"{CrawlerConfig.COURSESEL_BASE_URL}/tpm/findLessonTasksPreview_ElectTurn.action"
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
            response = self.session.get(full_url, timeout=CrawlerConfig.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and "data" in data and "lessonTasks" in data["data"]:
                return data["data"]["lessonTasks"]
            return []
        except Exception as e:
            logger.error(f"Error crawling lesson tasks: {e}")
            return []

    def crawl_course_catalog(self):
        """
        Crawl course catalog data with detailed descriptions

        Returns:
            dict: Dictionary mapping course IDs to course information
        """
        self._ensure_initialized()

        url = f"{CrawlerConfig.COURSESEL_BASE_URL}/jdji/tpm/findOwnCollegeCourse_JiCourse.action"

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
        except Exception as e:
            logger.error(f"Error crawling course catalog: {e}")
            return {}

    def crawl_prerequisites(self):
        """
        Crawl prerequisite data with course requirements and logic

        Returns:
            dict: Dictionary mapping course IDs to prerequisite lists
        """
        self._ensure_initialized()

        url = (
            f"{CrawlerConfig.COURSESEL_BASE_URL}/tpm/findAll_PrerequisiteCourse.action"
        )

        try:
            logger.info(f"Requesting Prerequisites API: {url}")
            response = self.session.post(url, json={})
            response.raise_for_status()

            if not response.text.strip():
                logger.warning("Prerequisites API returned empty response")
                return {}

            data = response.json()

            if data.get("success") and "data" in data:
                raw_prereqs = data["data"]
                logger.debug(f"Raw prerequisites data: {len(raw_prereqs)} items")

                prereqs = defaultdict(list)
                for item in raw_prereqs:
                    course_id = item.get("courseId")
                    if course_id:
                        prereqs[course_id].append(item)

                logger.debug(
                    f"Grouped prerequisites: {len(prereqs)} course IDs have prereqs"
                )
                return dict(prereqs)
            else:
                logger.warning("Prerequisites API failed or no data")
                return {}
        except Exception as e:
            logger.error(f"Prerequisites API error: {str(e)}")
            return {}

    def _get_current_elect_turn_id(self):
        """
        Get current election turn ID dynamically

        Returns:
            str: Current election turn ID

        Raises:
            RuntimeError: If unable to retrieve election turn ID
        """
        url = f"{CrawlerConfig.COURSESEL_BASE_URL}/tpm/findStudentElectTurns_ElectTurn.action"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()

            if data and isinstance(data, list) and len(data) > 0:
                current_turn = data[0]
                elect_turn_id = current_turn.get("electTurnId")
                if elect_turn_id:
                    logger.debug(f"Found current electTurnId: {elect_turn_id}")
                    return elect_turn_id

            logger.error("Could not find current electTurnId in API response")
            raise ValueError(
                "Unable to get current electTurnId - API returned no valid election turns"
            )
        except Exception as e:
            logger.error(f"Error getting electTurnId: {e}")
            raise RuntimeError(f"Failed to retrieve electTurnId from API: {e}") from e


class OfficialWebsiteCrawler:
    """
    Official JI Website Crawler

    Handles asynchronous crawling of course data from the official JI SJTU website.
    Provides detailed course descriptions and additional course information.
    """

    def __init__(self):
        """Initialize the Official Website crawler"""
        logger.info("OfficialWebsiteCrawler created")

    async def crawl_official_data(self):
        """
        Crawl course data from the official JI website

        Returns:
            dict: Dictionary mapping course codes to course information
        """
        logger.info("Fetching course data from official website")

        try:
            return await self._crawl_official_data_async()
        except Exception as e:
            logger.error(f"Error fetching official website data: {str(e)}")
            return {}

    async def _crawl_official_data_async(self):
        """
        Optimized async version of official website data fetching with enhanced concurrency

        Returns:
            dict: Dictionary mapping course codes to course information
        """
        # Get all course URLs from official website
        official_urls = self._get_official_course_urls()

        logger.info(f"Found {len(official_urls)} official course URLs")

        if not official_urls:
            logger.warning("No official course URLs found")
            return {}

        # Configure optimized timeout and session settings
        timeout = aiohttp.ClientTimeout(
            total=CrawlerConfig.REQUEST_TIMEOUT,
            connect=CrawlerConfig.CONNECT_TIMEOUT,
            sock_read=CrawlerConfig.READ_TIMEOUT,
        )

        headers = CrawlerConfig.DEFAULT_HEADERS.copy()
        headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
        )

        # Create connector with balanced performance and stability settings
        connector = aiohttp.TCPConnector(
            limit=CrawlerConfig.MAX_CONNECTIONS,
            limit_per_host=CrawlerConfig.CONNECTIONS_PER_HOST,
            ttl_dns_cache=CrawlerConfig.DNS_CACHE_TTL,
            use_dns_cache=True,
            keepalive_timeout=CrawlerConfig.KEEPALIVE_TIMEOUT,
            enable_cleanup_closed=True,
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector,
            read_bufsize=CrawlerConfig.READ_BUFFER_SIZE,
        ) as session:
            # Balanced concurrent requests for stability
            semaphore = asyncio.Semaphore(CrawlerConfig.CONCURRENT_REQUESTS)

            # Create tasks for all URLs
            tasks = [
                self._crawl_single_course_async(session, semaphore, url)
                for url in official_urls
            ]

            # Execute all tasks concurrently
            official_data = {}
            try:
                logger.info(
                    f"Starting to crawl {len(tasks)} URLs with {CrawlerConfig.CONCURRENT_REQUESTS} concurrent requests"
                )
                results = await asyncio.gather(*tasks, return_exceptions=True)

                successful = 0
                failed = 0

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed += 1
                        logger.warning(f"Failed to crawl course {i + 1}: {str(result)}")
                        continue

                    if (
                        result
                        and isinstance(result, dict)
                        and result.get("course_code")
                    ):
                        successful += 1
                        official_data[result["course_code"]] = result
                    else:
                        failed += 1

                logger.info(
                    f"Successfully extracted {len(official_data)} courses from {len(tasks)} URLs"
                )
                logger.info(f"Final stats - Success: {successful}, Failed: {failed}")

            except Exception as e:
                logger.error(f"Batch crawling failed: {str(e)}")
                return {}

            return official_data

    async def _crawl_single_course_async(self, session, semaphore, course_url):
        """
        Crawl single course data from official website asynchronously

        Args:
            session: aiohttp session
            semaphore: asyncio semaphore for concurrency control
            course_url (str): URL of the course page to crawl

        Returns:
            dict or None: Course data or None if failed
        """
        async with semaphore:
            try:
                for attempt in range(CrawlerConfig.MAX_RETRIES + 1):
                    try:
                        async with session.get(course_url) as response:
                            if response.status == 200:
                                html_content = await response.text()
                                return self._parse_official_course_html(
                                    html_content, course_url
                                )
                            elif response.status in [429, 503, 502, 504]:
                                if attempt < CrawlerConfig.MAX_RETRIES:
                                    await asyncio.sleep(
                                        CrawlerConfig.RETRY_DELAY * (attempt + 1)
                                    )
                                    continue
                            return None

                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        if attempt < CrawlerConfig.MAX_RETRIES:
                            await asyncio.sleep(
                                CrawlerConfig.RETRY_DELAY * (attempt + 1)
                            )
                            continue
                        else:
                            logger.debug(
                                f"Failed to fetch {course_url} after {CrawlerConfig.MAX_RETRIES + 1} attempts: {str(e)}"
                            )
                            return None

                return None

            except Exception as e:
                logger.debug(f"Unexpected error fetching {course_url}: {str(e)}")
                return None

    def _parse_official_course_html(self, html_content, course_url):
        """
        Parse HTML content to extract course data

        Args:
            html_content (str): HTML content of the course page
            course_url (str): URL of the course page

        Returns:
            dict or None: Parsed course data or None if failed
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "lxml")

            course_heading = soup.find("h2")
            if not course_heading:
                return None

            course_heading_text = course_heading.get_text()
            if not course_heading_text:
                return None

            split_course_heading = course_heading_text.split(" – ")
            if len(split_course_heading) < 2:
                return None

            text_inner_sections = soup.find_all(class_="et_pb_text_inner")
            if len(text_inner_sections) < 4:
                return None

            course_code = split_course_heading[0]
            course_title = split_course_heading[1]

            # Extract course information including instructors
            content_section = text_inner_sections[3]

            description = ""
            course_topics = []
            instructors = []

            # Get all text content and parse it
            all_text = content_section.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in all_text.split("\n") if line.strip()]

            current_section = None
            for i, line in enumerate(lines):
                if "Description:" in line:
                    current_section = "description"
                    continue
                elif "Course Topics:" in line or "Course topics:" in line:
                    current_section = "topics"
                    continue
                elif "Instructors:" in line:
                    current_section = "instructors"
                    continue
                elif "Credits:" in line or "Pre-requisites:" in line:
                    # Stop parsing when we hit credits or prerequisites
                    current_section = None
                    continue
                elif line and current_section == "description":
                    if not any(
                        x in line
                        for x in [
                            "Course Topics",
                            "Instructors",
                            "Credits",
                            "Pre-requisites",
                        ]
                    ):
                        description = f"{description} {line}".strip()
                elif line and current_section == "topics":
                    clean_line = line.lstrip("-*•").strip()
                    if (
                        clean_line
                        and len(course_topics) < CrawlerConfig.MAX_COURSE_TOPICS
                    ):
                        course_topics.append(clean_line)
                elif line and current_section == "instructors":
                    # Stop if we encounter credits or prerequisites
                    if any(
                        keyword in line for keyword in ["Credits:", "Pre-requisites:"]
                    ):
                        break

                    # Parse instructors - they might be separated by semicolons or commas
                    instructor_names = []
                    for separator in [";", ","]:
                        if separator in line:
                            instructor_names = [
                                name.strip()
                                for name in line.split(separator)
                                if name.strip()
                            ]
                            break
                    else:
                        instructor_names = [line.strip()] if line.strip() else []

                    instructors.extend(instructor_names)

            return {
                "course_code": course_code,
                "course_title": course_title,
                "description": description.strip(),
                "course_topics": course_topics,
                "instructors": instructors,
                "official_url": course_url,
            }

        except Exception:
            return None

    def _get_official_course_urls(self):
        """
        Get all course URLs from official website

        Returns:
            set: Set of course URLs
        """
        try:
            from bs4 import Tag

            soup = retrieve_soup(CrawlerConfig.OFFICIAL_ORC_BASE_URL)

            if not soup:
                logger.error("Failed to retrieve soup from official website")
                return set()

            linked_urls = []

            for a in soup.find_all("a", href=True):
                if isinstance(a, Tag) and a.has_attr("href"):
                    href = a["href"]
                    if href and isinstance(href, str):
                        full_url = urljoin(CrawlerConfig.OFFICIAL_BASE_URL, href)
                        linked_urls.append(full_url)

            course_urls = {
                linked_url
                for linked_url in linked_urls
                if self._is_official_course_url(linked_url)
            }

            logger.info(f"Found {len(course_urls)} course URLs from official website")
            return course_urls

        except Exception as e:
            logger.error(f"Error getting official course URLs: {str(e)}")
            return set()

    def _is_official_course_url(self, candidate_url):
        """
        Check if URL is a valid official course detail URL

        Args:
            candidate_url (str): URL to validate

        Returns:
            bool: True if URL is a course detail page
        """
        return candidate_url.startswith(CrawlerConfig.OFFICIAL_COURSE_DETAIL_URL_PREFIX)


class CourseDataIntegrator:
    """
    Course Data Integrator

    Handles integration of course data from multiple sources:
    - Course Selection System APIs
    - Official Website data
    - Data normalization and standardization
    """

    def __init__(self):
        """Initialize the Course Data Integrator"""
        logger.info("CourseDataIntegrator created")

    def integrate_data(
        self,
        lesson_tasks_data,
        course_catalog_data,
        prerequisites_data,
        official_data=None,
    ):
        """
        Integrate course data from multiple sources with course catalog as primary source

        Args:
            lesson_tasks_data (list): Lesson task data from course selection API
            course_catalog_data (dict): Course catalog data from course selection API
            prerequisites_data (dict): Prerequisites data from course selection API
            official_data (dict, optional): Official website data

        Returns:
            list: List of integrated course records
        """
        if official_data is None:
            official_data = {}

        logger.info(
            f"Starting integration with {len(lesson_tasks_data)} lesson tasks, "
            f"{len(course_catalog_data)} catalog courses, {len(prerequisites_data)} prereq groups, "
            f"{len(official_data)} official records"
        )

        integrated_courses = []
        courses_with_prereqs = 0

        # Create indexes for efficient lookup
        lesson_tasks_by_code = self._create_lesson_tasks_index(lesson_tasks_data)
        official_by_code = self._create_official_data_index(official_data)
        prereq_by_code = self._create_prerequisites_index(
            prerequisites_data, course_catalog_data
        )

        # Get all unique course codes
        all_course_codes = self._get_all_course_codes(
            course_catalog_data, official_by_code
        )

        logger.info(f"Processing {len(all_course_codes)} unique course codes")

        # Process each course code
        for course_code in all_course_codes:
            catalog_info = self._find_catalog_info(course_code, course_catalog_data)
            lesson_tasks_list = lesson_tasks_by_code.get(course_code, [])
            official_info = official_by_code.get(course_code, {})
            prereq_info = prereq_by_code.get(course_code, [])

            # Merge lesson tasks sections if available
            merged_lesson_tasks = (
                self._merge_course_sections(lesson_tasks_list)
                if lesson_tasks_list
                else {}
            )

            if prereq_info:
                courses_with_prereqs += 1
                logger.debug(
                    f"Course {course_code} has {len(prereq_info)} prerequisites"
                )

            # Build course record
            course_data = self._build_course_record(
                course_code,
                merged_lesson_tasks,
                catalog_info,
                prereq_info,
                official_info,
            )

            if course_data:
                integrated_courses.append(course_data)

        logger.info(
            f"Integration complete: {courses_with_prereqs} courses have prerequisites, "
            f"{len(integrated_courses)} total courses"
        )
        return integrated_courses

    def _create_lesson_tasks_index(self, lesson_tasks_data):
        """Create index of lesson tasks by course code"""
        lesson_tasks_by_code = defaultdict(list)
        if lesson_tasks_data:
            for course in lesson_tasks_data:
                course_code = course.get("courseCode")
                if course_code:
                    lesson_tasks_by_code[course_code].append(course)
        return lesson_tasks_by_code

    def _create_official_data_index(self, official_data):
        """Create index of official data by course code"""
        official_by_code = {}
        if official_data:
            for course_code, official_info in official_data.items():
                official_by_code[course_code] = official_info
        return official_by_code

    def _create_prerequisites_index(self, prerequisites_data, course_catalog_data):
        """Create index of prerequisites by course code"""
        prereq_by_code = {}
        if prerequisites_data:
            for course_id, prereq_list in prerequisites_data.items():
                if isinstance(course_catalog_data, dict):
                    catalog_info = course_catalog_data.get(course_id)
                    if catalog_info:
                        course_code = catalog_info.get("courseCode")
                        if course_code:
                            prereq_by_code[course_code] = prereq_list
        return prereq_by_code

    def _get_all_course_codes(self, course_catalog_data, official_by_code):
        """Get all unique course codes from all sources"""
        all_course_codes = set()

        if isinstance(course_catalog_data, dict):
            for course_id, catalog_info in course_catalog_data.items():
                course_code = catalog_info.get("courseCode")
                if course_code:
                    all_course_codes.add(course_code)
        elif isinstance(course_catalog_data, list):
            for catalog_info in course_catalog_data:
                course_code = catalog_info.get("courseCode")
                if course_code:
                    all_course_codes.add(course_code)

        # Add course codes that only exist in official data
        all_course_codes.update(official_by_code.keys())

        return all_course_codes

    def _find_catalog_info(self, course_code, course_catalog_data):
        """Find catalog information for a specific course code"""
        catalog_info = {}
        if isinstance(course_catalog_data, dict):
            for course_id, info in course_catalog_data.items():
                if info.get("courseCode") == course_code:
                    catalog_info = info
                    break
        elif isinstance(course_catalog_data, list):
            for info in course_catalog_data:
                if info.get("courseCode") == course_code:
                    catalog_info = info
                    break
        return catalog_info

    def _merge_course_sections(self, course_list):
        """
        Merge sections of the same course

        Args:
            course_list (list): List of course sections

        Returns:
            dict: Merged course data
        """
        if not course_list:
            return {}

        merged = course_list[0].copy()
        all_instructors = set()

        for course in course_list:
            teachers = course.get("lessonTaskTeam", "")
            if teachers:
                for teacher in re.split(r"[,;]", teachers):
                    if teacher.strip():
                        all_instructors.add(teacher.strip())

        merged["all_instructors"] = list(all_instructors)
        return merged

    def _build_course_record(
        self, course_code, main_data, catalog_data, prereq_data, official_data=None
    ):
        """
        Build standardized course record from multiple data sources

        Args:
            course_code (str): Course code
            main_data (dict): Main course data (lesson tasks)
            catalog_data (dict): Catalog course data
            prereq_data (list): Prerequisites data
            official_data (dict, optional): Official website data

        Returns:
            dict or None: Standardized course record or None if invalid
        """
        if official_data is None:
            official_data = {}

        course_title = self._extract_course_title(
            main_data, catalog_data, official_data
        )
        if not course_title:
            return None

        department, number = self._parse_course_code(course_code)
        course_credits = self._extract_course_credits(main_data, catalog_data)
        prerequisites = self._build_prerequisites_string(course_code, prereq_data)

        # Description and topics only from official data
        description = self._extract_description(official_data) if official_data else ""
        course_topics = official_data.get("course_topics", []) if official_data else []
        official_url = official_data.get("official_url", "") if official_data else ""

        # Instructors from multiple sources with priority: lesson tasks > catalog > official
        instructors = self._extract_instructors(main_data, catalog_data, official_data)

        # Use official URL as primary URL, fallback to API URL if not available
        course_url = official_url or self._build_course_url(main_data)

        return {
            "course_code": course_code,
            "course_title": course_title,
            "department": department,
            "number": number,
            "course_credits": course_credits,
            "pre_requisites": prerequisites,
            "description": description,
            "course_topics": course_topics,
            "instructors": instructors,
            "url": course_url,
            "official_url": official_url,
        }

    def _extract_course_title(self, main_data, catalog_data, official_data=None):
        """
        Extract course title with preference for English names

        Args:
            main_data (dict): Main course data
            catalog_data (dict): Catalog course data
            official_data (dict, optional): Official website data

        Returns:
            str: Course title
        """
        if official_data is None:
            official_data = {}
        if main_data is None:
            main_data = {}
        if catalog_data is None:
            catalog_data = {}

        return (
            official_data.get("course_title", "")
            or main_data.get("courseNameEn", "")
            or main_data.get("courseName", "")
            or catalog_data.get("courseNameEn", "")
            or catalog_data.get("courseName", "")
        ).strip()

    def _parse_course_code(self, course_code):
        """
        Parse course code to extract department and number

        Args:
            course_code (str): Course code to parse

        Returns:
            tuple: (department, number) where department is str and number is int
        """
        department = ""
        number = 0

        if course_code:
            code_upper = course_code.upper()

            # Try standard format first: DEPT###(#)?J? (3 or 4 digits, J is optional)
            match = re.match(r"^([A-Z]{2,4})(\d{3,4})J?$", code_upper)
            if match:
                department = match.group(1)
                number = int(match.group(2))
            else:
                # Try alternative formats for non-standard course codes
                alt_match = re.match(r"^([A-Z]+)(\d+)$", code_upper)
                if alt_match:
                    department = alt_match.group(1)
                    try:
                        number = int(alt_match.group(2))
                    except ValueError:
                        number = 0
                else:
                    # For complex codes like "VE507(5002)", extract the main part
                    complex_match = re.match(r"^([A-Z]{2,4})(\d{3,4})", code_upper)
                    if complex_match:
                        department = complex_match.group(1)
                        try:
                            number = int(complex_match.group(2))
                        except ValueError:
                            number = 0

        return department, number

    def _extract_course_credits(self, main_data, catalog_data):
        """
        Extract course credits from available data sources

        Args:
            main_data (dict): Main course data
            catalog_data (dict): Catalog course data

        Returns:
            int: Course credits
        """
        if main_data is None:
            main_data = {}
        if catalog_data is None:
            catalog_data = {}

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
        """
        Build prerequisites string from API data

        Args:
            course_code (str): Course code
            prereq_data (list): Prerequisites data

        Returns:
            str: Formatted prerequisites string
        """
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
            # Convert Chinese terms to English
            prerequisites = self._normalize_prerequisites_to_english(prerequisites)
            logger.debug(f"Final prerequisites for {course_code}: {prerequisites}")
            return prerequisites

        return ""

    def _normalize_prerequisites_to_english(self, prerequisites_text):
        """
        Convert Chinese prerequisite terms to English

        Args:
            prerequisites_text (str): Prerequisites text with potential Chinese terms

        Returns:
            str: Normalized text with English terms
        """
        if not prerequisites_text:
            return ""

        normalized_text = prerequisites_text
        for (
            chinese_term,
            english_term,
        ) in CrawlerConfig.CHINESE_TO_ENGLISH_TRANSLATIONS.items():
            normalized_text = normalized_text.replace(chinese_term, english_term)

        return normalized_text

    def _extract_description(self, official_data=None):
        """
        Extract course description from official website data

        Args:
            official_data (dict, optional): Official website data

        Returns:
            str: Course description
        """
        if official_data is None:
            official_data = {}

        return official_data.get("description", "").strip()

    def _extract_instructors(self, main_data, catalog_data, official_data=None):
        """
        Extract and merge instructor information from multiple sources
        Priority: 1) lesson tasks, 2) catalog data, 3) official website

        Args:
            main_data (dict): Main course data
            catalog_data (dict): Catalog course data
            official_data (dict): Official website course data

        Returns:
            list: List of instructor names
        """
        if main_data is None:
            main_data = {}
        if catalog_data is None:
            catalog_data = {}
        if official_data is None:
            official_data = {}

        instructors = []

        # Priority 1: Extract from lesson tasks data
        lesson_task_team = main_data.get("lessonTaskTeam", "").strip()
        if lesson_task_team:
            instructors.append(lesson_task_team)

        # Check for firstSpeakerName field
        first_speaker = main_data.get("firstSpeakerName", "").strip()
        if first_speaker and first_speaker not in instructors:
            instructors.append(first_speaker)

        # Check for all_instructors field (backward compatibility)
        all_instructors = main_data.get("all_instructors", [])
        if isinstance(all_instructors, list):
            for instructor in all_instructors:
                if instructor.strip() and instructor.strip() not in instructors:
                    instructors.append(instructor.strip())

        # Priority 2: Extract from catalog data (teacherName field)
        teacher_name = catalog_data.get("teacherName", "").strip()
        if teacher_name:
            for teacher in re.split(r"[,;]", teacher_name):
                teacher = teacher.strip()
                if teacher and teacher not in instructors:
                    instructors.append(teacher)

        # Priority 3: Extract from official website data (fallback)
        if not instructors:  # Only use if no instructors found from other sources
            official_instructors = official_data.get("instructors", [])
            if isinstance(official_instructors, list):
                for instructor in official_instructors:
                    if instructor.strip() and instructor.strip() not in instructors:
                        instructors.append(instructor.strip())

        return instructors

    def _build_course_url(self, main_data):
        """
        Build course detail page URL

        Args:
            main_data (dict): Main course data

        Returns:
            str: Course detail URL or empty string
        """
        if main_data is None:
            main_data = {}
        course_id = main_data.get("courseId")
        return f"{COURSE_DETAIL_URL_PREFIX}{course_id}" if course_id else ""
