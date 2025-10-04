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

# API endpoints for course selection system
BASE_URL = "https://coursesel.umji.sjtu.edu.cn"
COURSE_DETAIL_URL_PREFIX = urllib.parse.urljoin(BASE_URL, "/course/")

# Official website endpoints for detailed course info
OFFICIAL_BASE_URL = "https://www.ji.sjtu.edu.cn/"
OFFICIAL_ORC_BASE_URL = urljoin(
    OFFICIAL_BASE_URL, "/academics/courses/courses-by-number/"
)
OFFICIAL_COURSE_DETAIL_URL_PREFIX = (
    "https://www.ji.sjtu.edu.cn/academics/courses/courses-by-number/course-info/?id="
)
OFFICIAL_UNDERGRAD_URL = OFFICIAL_ORC_BASE_URL


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

    def get_all_courses(self, use_cache=True, save_cache=True):
        """
        Get all course data from multiple APIs and official website

        Args:
            use_cache: Whether to use cached data
            save_cache: Whether to save data to cache

        Returns:
            list: Course data with prerequisites, descriptions, and instructors
        """
        cache_manager = CourseDataCache()

        # If using cache, check for available cache files first
        if use_cache:
            cache_files = cache_manager.list_cache_files()
            if cache_files:
                print(f"Found {len(cache_files)} cache files")
                choice = input("Use existing cache? (y/n/list): ").strip().lower()

                if choice == "list":
                    # Show cache file list for selection
                    from apps.spider.manager import interactive_cache_manager

                    selected_file = interactive_cache_manager()
                    if selected_file:
                        print(f"Loading cache file: {selected_file.name}")
                        return cache_manager.load_from_jsonl(selected_file)
                elif choice in ["y", "yes"]:
                    # Use the latest cache file
                    latest_file = cache_files[0]
                    print(f"Loading latest cache: {latest_file.name}")
                    return cache_manager.load_from_jsonl(latest_file)

        # Ask user to choose data sources
        use_coursesel = self._ask_user_choice(
            "Crawl course selection system data? (y/n): ", default="n"
        )
        use_official = self._ask_user_choice(
            "Crawl official website data? (y/n): ", default="y"
        )

        courses_data = []
        course_details = {}
        prerequisites = {}
        official_data = {}

        if use_coursesel:
            self._ensure_initialized()  # Make sure crawler is initialized
            print("🌐 爬取课程选择系统数据...")
            # Get data from course selection APIs
            courses_data = self._get_lesson_tasks()
            course_details = self._get_course_catalog()
            prerequisites = self._get_prerequisites()
        else:
            print("⏭️ 跳过课程选择系统数据")

        if use_official:
            print("🌐 爬取官网数据...")
            # Get official website data for enhanced descriptions
            official_data = self._get_official_website_data()
        else:
            print("Skipping official website data")

        # Integrate data
        integrated_data = self._integrate_course_data(
            courses_data, course_details, prerequisites, official_data
        )

        print(
            f"DEBUG: Integrated data count: {len(integrated_data) if integrated_data else 0}"
        )
        print(f"DEBUG: Save cache enabled: {save_cache}")

        # Save to cache
        if save_cache and integrated_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_sources = []
            if use_coursesel:
                data_sources.append("coursesel")
            if use_official:
                data_sources.append("official")

            cache_filename = f"courses_{'_'.join(data_sources)}"
            cache_filepath = cache_manager.save_to_jsonl(
                integrated_data, cache_filename, timestamp
            )

            print(f"Data cached to: {cache_filepath}")

            # Ask whether to import to database immediately
            from apps.spider.manager import preview_data_before_import

            if preview_data_before_import(cache_filepath, limit=5):
                print("Starting database import...")
                try:
                    import_department(integrated_data)
                    print("Data import successful!")
                except Exception as e:
                    print(f"Data import failed: {str(e)}")
                    print("Data saved to cache, can be imported manually later")
            else:
                print("Skipping database import, data saved to cache")

        return integrated_data

    def _ask_user_choice(self, prompt, default="y"):
        """Ask user for yes/no choice with default value"""
        while True:
            response = input(prompt).strip().lower()
            if not response:
                response = default.lower()
            if response in ["y", "yes", "true"]:
                return True
            elif response in ["n", "no", "false"]:
                return False
            else:
                print("Please enter y/yes or n/no")

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

            logger.error("Could not find current electTurnId in API response")
            raise ValueError(
                "Unable to get current electTurnId - API returned no valid election turns"
            )
        except Exception as e:
            logger.error(f"Error getting electTurnId: {e}")
            raise RuntimeError(f"Failed to retrieve electTurnId from API: {e}") from e

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

    def _get_official_website_data(self):
        """Get course data from official JI website for enhanced descriptions"""
        logger.info("Fetching course data from official website")

        try:
            # Run the async crawler
            return asyncio.run(self._get_official_website_data_async())
        except Exception as e:
            logger.error(f"Error fetching official website data: {str(e)}")
            return {}

    async def _get_official_website_data_async(self):
        """Optimized async version of official website data fetching with enhanced concurrency"""
        # Get all course URLs from official website
        official_urls = self._get_official_course_urls()

        print(f"DEBUG: Found {len(official_urls)} official course URLs")

        if not official_urls:
            logger.warning("No official course URLs found")
            return {}

        logger.info(f"Found {len(official_urls)} course URLs to crawl")

        # Optimized timeout and session settings for maximum speed
        timeout = aiohttp.ClientTimeout(total=15, connect=3, sock_read=10)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

        # Create connector with balanced performance and stability settings
        connector = aiohttp.TCPConnector(
            limit=50,  # Reduced total connection pool size
            limit_per_host=25,  # Reduced connections per host
            ttl_dns_cache=600,  # Longer DNS cache for 10 minutes
            use_dns_cache=True,
            keepalive_timeout=30,  # Shorter keepalive to prevent hangs
            enable_cleanup_closed=True,
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector,
            read_bufsize=32768,  # Smaller read buffer for stability
        ) as session:
            # Balanced concurrent requests for stability
            semaphore = asyncio.Semaphore(20)  # Reduced to 20 concurrent requests

            # Create tasks for all URLs
            tasks = [
                self._crawl_official_course_data_async(session, semaphore, url)
                for url in official_urls
            ]

            # Execute all tasks concurrently with better progress tracking
            official_data = {}
            completed = 0
            total = len(tasks)

            # Use gather for better performance than as_completed
            try:
                print(
                    f"DEBUG: Starting to crawl {total} URLs with 20 concurrent requests..."
                )
                results = await asyncio.gather(*tasks, return_exceptions=True)

                print(f"DEBUG: Received {len(results)} results")

                successful = 0
                failed = 0

                for i, result in enumerate(results):
                    completed += 1

                    # More frequent progress reporting for better visibility
                    if completed % 20 == 0 or completed == total:
                        print(
                            f"DEBUG: Progress: {completed}/{total} ({completed / total * 100:.1f}%) - Success: {successful}, Failed: {failed}"
                        )
                        logger.info(
                            f"Progress: {completed}/{total} courses processed ({completed / total * 100:.1f}%)"
                        )

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

            except Exception as e:
                print(f"DEBUG: Batch crawling failed: {str(e)}")
                logger.error(f"Batch crawling failed: {str(e)}")
                return {}

            print(
                f"DEBUG: Successfully extracted {len(official_data)} courses from {total} URLs"
            )
            print(f"DEBUG: Final stats - Success: {successful}, Failed: {failed}")
            logger.info(
                f"Successfully fetched official data for {len(official_data)} courses out of {total} total"
            )
            return official_data

    async def _crawl_official_course_data_async(self, session, semaphore, course_url):
        """Ultra-optimized async crawl single course data from official website"""
        async with semaphore:  # Limit concurrent requests
            try:
                # Balanced retry logic for stability
                max_retries = 2  # Increased retries for stability
                retry_delay = 1.0  # Longer retry delay

                for attempt in range(max_retries + 1):
                    try:
                        async with session.get(course_url) as response:
                            if response.status == 200:
                                html_content = await response.text()
                                return self._parse_official_course_html(
                                    html_content, course_url
                                )
                            elif response.status in [
                                429,
                                503,
                                502,
                                504,
                            ]:  # Retry on server errors
                                if attempt < max_retries:
                                    await asyncio.sleep(
                                        retry_delay * (attempt + 1)
                                    )  # Exponential backoff
                                    continue
                            # Don't retry on other errors, fail fast
                            return None

                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        if attempt < max_retries:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            logger.debug(
                                f"Failed to fetch {course_url} after {max_retries + 1} attempts: {str(e)}"
                            )
                            return None

                return None

            except Exception as e:
                logger.debug(f"Unexpected error fetching {course_url}: {str(e)}")
                return None

    def _parse_official_course_html(self, html_content, course_url):
        """Ultra-fast HTML parsing for course data extraction"""
        try:
            from bs4 import BeautifulSoup

            # Use faster lxml parser for better performance
            soup = BeautifulSoup(html_content, "lxml")

            course_heading = soup.find("h2")
            if not course_heading:
                print(f"DEBUG: No h2 heading found in {course_url}")
                return None

            course_heading_text = course_heading.get_text()
            if not course_heading_text:
                print(f"DEBUG: Empty h2 text in {course_url}")
                return None

            split_course_heading = course_heading_text.split(" – ")
            if len(split_course_heading) < 2:
                print(
                    f"DEBUG: Invalid heading format '{course_heading_text}' in {course_url}"
                )
                return None

            # Fast extraction with minimal processing
            text_inner_sections = soup.find_all(class_="et_pb_text_inner")
            if len(text_inner_sections) < 4:
                print(
                    f"DEBUG: Insufficient text sections ({len(text_inner_sections)}) in {course_url}"
                )
                return None

            course_code = split_course_heading[0]
            course_title = split_course_heading[1]

            print(f"DEBUG: Successfully parsed {course_code} - {course_title}")

            # Fast description and topics extraction
            description = ""
            course_topics = []

            # Get all text content at once for faster processing
            content_section = text_inner_sections[3]
            all_text = content_section.get_text(separator="\n", strip=True)

            # Simple text processing for speed
            lines = [line.strip() for line in all_text.split("\n") if line.strip()]

            in_description = False
            in_topics = False

            for i, line in enumerate(lines):
                if "Description:" in line:
                    in_description = True
                    continue
                elif "Course Topics:" in line or "Course topics:" in line:
                    in_description = False
                    in_topics = True
                    continue
                elif (
                    in_description
                    and line
                    and not any(
                        x in line for x in ["Course Topics", "Lectures", "Seminars"]
                    )
                ):
                    if description:
                        description += " " + line
                    else:
                        description = line
                elif in_topics and line:
                    # Simple topic extraction
                    clean_line = line.lstrip("•-*").strip()
                    if clean_line and len(course_topics) < 10:  # Limit for performance
                        course_topics.append(clean_line)

            return {
                "course_code": course_code,
                "course_title": course_title,
                "description": description.strip(),
                "course_topics": course_topics,
                "official_url": course_url,
            }

        except Exception:
            # Fast fail for maximum performance
            return None

    def _get_official_course_urls(self):
        """Get all course URLs from official website"""
        try:
            from bs4 import Tag

            print(f"DEBUG: Fetching course URLs from {OFFICIAL_UNDERGRAD_URL}")
            soup = retrieve_soup(OFFICIAL_UNDERGRAD_URL)

            if not soup:
                print("DEBUG: Failed to retrieve soup from official website")
                return set()

            linked_urls = []

            for a in soup.find_all("a", href=True):
                # Check if it's a Tag element and has href attribute
                if isinstance(a, Tag) and a.has_attr("href"):
                    href = a["href"]
                    if href and isinstance(href, str):
                        full_url = urljoin(OFFICIAL_BASE_URL, href)
                        linked_urls.append(full_url)

            print(f"DEBUG: Found {len(linked_urls)} total links")

            course_urls = {
                linked_url
                for linked_url in linked_urls
                if self._is_official_course_url(linked_url)
            }

            print(f"DEBUG: Filtered to {len(course_urls)} course URLs")
            if len(course_urls) > 0:
                print(f"DEBUG: Sample course URL: {list(course_urls)[0]}")

            return course_urls

        except Exception as e:
            print(f"DEBUG: Error getting official course URLs: {str(e)}")
            logger.error(f"Error getting official course URLs: {str(e)}")
            return set()

    def _is_official_course_url(self, candidate_url):
        """Check if URL is a valid official course detail URL"""
        return candidate_url.startswith(OFFICIAL_COURSE_DETAIL_URL_PREFIX)

    def _integrate_course_data(
        self, courses_data, course_details, prerequisites, official_data=None
    ):
        """Integrate course data from multiple sources"""
        if official_data is None:
            official_data = {}

        logger.info(
            f"Starting integration with {len(courses_data)} courses, {len(prerequisites)} prereq groups, {len(official_data)} official records"
        )

        integrated_courses = []
        courses_with_prereqs = 0

        # If we have course selection data, process it
        if courses_data and len(courses_data) > 0:
            courses_by_code = defaultdict(list)
            for course in courses_data:
                course_code = course.get("courseCode")
                if course_code:
                    courses_by_code[course_code].append(course)

            for course_code, course_list in courses_by_code.items():
                merged = self._merge_course_sections(course_list)
                if not merged:
                    continue

                course_id = merged.get("courseId")
                catalog_info = course_details.get(course_id, {})
                prereq_info = prerequisites.get(course_id, [])
                official_info = official_data.get(course_code, {})

                if prereq_info:
                    courses_with_prereqs += 1
                    logger.debug(
                        f"Course {course_code} (ID: {course_id}) has {len(prereq_info)} prereqs"
                    )

                course_data = self._build_course_record(
                    course_code, merged, catalog_info, prereq_info, official_info
                )

                if course_data:
                    integrated_courses.append(course_data)

        # If we only have official data (no course selection data), create courses from official data
        if (not courses_data or len(courses_data) == 0) and official_data:
            logger.info("Creating courses from official website data only")
            for course_code, official_info in official_data.items():
                # Create empty main_data for courses that only exist in official website
                empty_main_data = {}
                empty_catalog_data = {}
                empty_prereq_data = []

                course_data = self._build_course_record(
                    course_code,
                    empty_main_data,
                    empty_catalog_data,
                    empty_prereq_data,
                    official_info,
                )

                if course_data:
                    integrated_courses.append(course_data)

        logger.info(
            f"Integration complete: {courses_with_prereqs} courses have prerequisites, {len(integrated_courses)} total courses"
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

    def _build_course_record(
        self, course_code, main_data, catalog_data, prereq_data, official_data=None
    ):
        """Build standardized course record with official website data integration"""
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
        description = self._extract_description(official_data)
        instructors = self._extract_instructors(main_data, catalog_data)
        # Get course topics and official URL from official website data
        course_topics = official_data.get("course_topics", [])
        official_url = official_data.get("official_url", "")

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
        """Extract course title (prefer English name)"""
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
        department = ""
        number = 0

        if course_code:
            # Match DEPT###(#)?J? (3 or 4 digits, J is optional)
            match = re.match(r"^([A-Z]{2,4})(\d{3,4})J?$", course_code)
            if match:
                department = match.group(1)
                number = int(match.group(2))

        return department, number

    def _extract_course_credits(self, main_data, catalog_data):
        """Extract course credits"""
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
            # Convert Chinese terms to English
            prerequisites = self._normalize_prerequisites_to_english(prerequisites)
            logger.debug(f"Final prerequisites for {course_code}: {prerequisites}")
            return prerequisites

        return ""

    def _normalize_prerequisites_to_english(self, prerequisites_text):
        """Convert Chinese prerequisite terms to English"""
        if not prerequisites_text:
            return ""

        # Define translation mapping
        translations = {
            "已获学分": "Obtained Credit",
            "已提交学分": "Credits Submitted",
            "获得学分": "Obtained Credit",
            "提交学分": "Credits Submitted",
            "学分": "Credit",
        }

        # Apply translations
        normalized = prerequisites_text
        for chinese, english in translations.items():
            normalized = normalized.replace(chinese, english)

        return normalized

    def _extract_description(self, official_data=None):
        """Extract course description (only from official website)"""
        if official_data is None:
            official_data = {}

        return official_data.get("description", "").strip()

    def _extract_instructors(self, main_data, catalog_data):
        """Extract and merge instructor information"""
        if main_data is None:
            main_data = {}
        if catalog_data is None:
            catalog_data = {}

        instructors = main_data.get("all_instructors", [])
        teacher_name = catalog_data.get("teacherName", "")

        if teacher_name:
            for teacher in re.split(r"[,;，；、]", teacher_name):
                if teacher.strip() and teacher.strip() not in instructors:
                    instructors.append(teacher.strip())

        return instructors

    def _build_course_url(self, main_data):
        """Build course detail page URL"""
        if main_data is None:
            main_data = {}
        course_id = main_data.get("courseId")
        return f"{COURSE_DETAIL_URL_PREFIX}{course_id}" if course_id else ""


_crawler = None
_course_data_cache = {}


def _get_crawler():
    """Get crawler instance (singleton pattern)"""
    global _crawler
    if _crawler is None:
        _crawler = CourseSelCrawler()
    return _crawler


def crawl_program_urls():
    """Get all course URLs (legacy interface)"""
    global _course_data_cache

    crawler = _get_crawler()
    courses = crawler.get_all_courses()

    course_urls = []
    _course_data_cache = {}  # Reset cache

    for course in courses:
        if course.get("url"):
            course_urls.append(course["url"])
            _course_data_cache[course["url"]] = course

    return course_urls


def _crawl_course_data(course_url):
    """Crawl single course data (legacy interface)"""
    global _course_data_cache

    course_data = _course_data_cache.get(course_url)
    if course_data:
        return course_data

    return {}


def import_department(department_data):
    """Import course data to database with improved error handling"""
    success_count = 0
    error_count = 0

    for course_data in department_data:
        try:
            # 验证必要字段
            required_fields = ["course_code", "course_title"]
            missing_fields = [
                field for field in required_fields if not course_data.get(field)
            ]

            if missing_fields:
                logger.warning(
                    f"Skipping course due to missing required fields: {missing_fields}"
                )
                error_count += 1
                continue

            # 准备默认值，处理可能缺失的字段
            defaults = {
                "course_title": course_data.get("course_title", ""),
                "department": course_data.get("department", ""),
                "number": course_data.get("number", 0),
                "course_credits": course_data.get("course_credits", 0),
                "pre_requisites": course_data.get("pre_requisites", ""),
                "description": course_data.get("description", ""),
                "course_topics": course_data.get("course_topics", []),
                "url": course_data.get("url", ""),
            }

            # 注意：official_url 字段不存在于Course模型中，所以不包含它

            # 创建或更新课程
            course, created = Course.objects.update_or_create(
                course_code=course_data["course_code"],
                defaults=defaults,
            )

            # 处理教师信息
            instructors = course_data.get("instructors", [])
            if instructors:
                for instructor_name in instructors:
                    if instructor_name.strip():  # 确保教师名字不为空
                        try:
                            instructor, _ = Instructor.objects.get_or_create(
                                name=instructor_name.strip()
                            )

                            offering, _ = CourseOffering.objects.get_or_create(
                                course=course,
                                term=CURRENT_TERM,
                                defaults={"section": 1, "period": ""},
                            )
                            offering.instructors.add(instructor)
                        except Exception as e:
                            logger.warning(
                                f"Error creating instructor {instructor_name}: {str(e)}"
                            )

            success_count += 1
            if created:
                logger.info(f"Created new course: {course_data['course_code']}")
            else:
                logger.info(f"Updated course: {course_data['course_code']}")

        except Exception as e:
            error_count += 1
            course_code = course_data.get("course_code", "Unknown")
            error_msg = str(e)
            print(f"Error importing course {course_code}: {error_msg}")
            logger.error(f"Error importing course {course_code}: {error_msg}")

    logger.info(f"Import completed: {success_count} successful, {error_count} errors")
    return {"success": success_count, "errors": error_count}


def extract_prerequisites(pre_requisites):
    """Process prerequisite string format (legacy function)"""
    result = pre_requisites

    result = result.replace("Pre-requisites:", "").strip()
    result = result.replace("Obtained Credit", "obtained_credit").strip()
    result = result.replace("Credits Submitted", "credits_submitted").strip()
    result = result.replace("&&", " && ").strip()
    result = result.replace("||", " || ").strip()

    return result
