import re
from urllib.parse import urljoin

import json
import requests
import time
from collections import defaultdict

from apps.web.models import Course, CourseOffering, Instructor
from lib.constants import CURRENT_TERM

# API端点配置
BASE_URL = "https://coursesel.umji.sjtu.edu.cn"
COURSE_DETAIL_URL_PREFIX = urljoin(BASE_URL, "/course/")

# 兼容性配置（保留旧版本接口）
ORC_BASE_URL = BASE_URL
UNDERGRAD_URL = BASE_URL

# 正则表达式模式
INSTRUCTOR_TERM_REGEX = re.compile(r"^(?P<name>\w*)\s?(\((?P<term>\w*)\))?")


class CourseSelCrawler:
    """
    JI SJTU 课程选择系统爬虫模块

    该模块负责从上海交通大学密西根学院的课程选择系统中爬取课程信息，
    包括课程基本信息、先修课程要求、教师信息等。

    数据源说明：
    1. 选课任务API: 提供当前学期的课程开设信息、教师信息等
    2. 课程目录API: 提供课程详细描述、额外的教师信息等
    3. 先修课程API: 提供完整的先修课程逻辑关系
    """

    def __init__(self):
        """
        初始化爬虫实例
        
        设置HTTP会话、cookies和headers，确保能够正常访问课程选择系统的API。
        """
        self.session = requests.Session()

        # 必要的认证cookies（从浏览器中获取的有效会话ID）
        cookies = {
            "JSESSIONID": "your_own_cookie",
        }
        self.session.cookies.update(cookies)

        # 模拟浏览器请求的headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://coursesel.umji.sjtu.edu.cn/",
            "X-Requested-With": "XMLHttpRequest",  # 标识AJAX请求
        }
        self.session.headers.update(headers)

    def get_all_courses(self):
        """
        获取所有课程数据的主入口方法
        
        该方法协调多个数据源，获取完整的课程信息：
        1. 选课任务数据（包含当前学期开设信息）
        2. 课程目录数据（包含课程描述等详细信息）
        3. 先修课程数据（包含先修要求的逻辑关系）
        
        Returns:
            list: 包含所有课程信息的字典列表，每个字典包含：
                - course_code: 课程代码
                - course_title: 课程标题
                - department: 院系代码
                - number: 课程编号
                - course_credits: 学分数
                - pre_requisites: 先修课程要求（字符串形式的逻辑表达式）
                - description: 课程描述
                - instructors: 教师列表
                - url: 课程详情页面URL
        """
        # 获取三个主要数据源
        courses_data = self._get_lesson_tasks()
        course_details = self._get_course_catalog()
        prerequisites = self._get_prerequisites()

        # 整合所有数据源的信息
        return self._integrate_course_data(courses_data, course_details, prerequisites)

    def _get_lesson_tasks(self):
        """
        获取选课任务数据（第一个数据源）
        
        从选课系统的主API获取当前学期的所有选课任务信息。
        这个API返回的数据包含：
        - 课程基本信息（课程代码、名称、学分等）
        - 教师信息
        - 开课时间和地点
        - 选课限制等信息
        
        Returns:
            list: 选课任务列表，每个任务包含课程的基本信息
        """
        url = f"{BASE_URL}/tpm/findLessonTasksPreview_ElectTurn.action"

        # API请求参数，控制返回的数据类型
        json_params = {
            "isToTheTime": True,  # 是否到了选课时间
            "electTurnId": "93B7BAF9-7E8B-4D32-BCC8-DE49B320AB0A",  # 选课轮次ID
            "loadCourseGroup": True,  # 加载课程组信息
            "loadElectTurn": True,  # 加载选课轮次信息
            "loadCourseType": True,  # 加载课程类型信息
            "loadCourseTypeCredit": True,  # 加载课程类型学分信息
            "loadElectTurnResult": True,  # 加载选课结果
            "loadStudentLessonTask": True,  # 加载学生选课任务
            "loadPrerequisiteCourse": True,  # 加载先修课程信息
            "loadLessonCalendarWeek": True,  # 加载课程日历周信息
            "loadLessonCalendarConflict": True,  # 加载时间冲突检查
            "loadTermCredit": True,  # 加载学期学分信息
            "loadLessonTask": True,  # 加载课程任务详情
            "loadDropApprove": True,  # 加载退课审批信息
            "loadElectApprove": True,  # 加载选课审批信息
        }

        # 构建GET请求URL（该API要求JSON参数作为查询字符串）
        import urllib.parse
        json_string = json.dumps(json_params, separators=(",", ":"))
        encoded_json = urllib.parse.quote(json_string)
        full_url = f"{url}?jsonString={encoded_json}"

        try:
            response = self.session.get(full_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # 检查API响应格式并提取课程任务数据
            if data.get("success") and "data" in data and "lessonTasks" in data["data"]:
                return data["data"]["lessonTasks"]
            return []
        except Exception:
            # 发生错误时返回空列表，不中断整个爬取流程
            return []

    def _get_course_catalog(self):
        """
        获取课程目录数据（第二个数据源）
        
        从课程目录API获取课程的详细描述信息。
        这个API主要提供：
        - 课程的详细描述
        - 课程的英文名称
        - 额外的教师信息
        - 其他补充信息
        
        Returns:
            dict: 以courseId为键的课程详情字典
        """
        url = f"{BASE_URL}/jdji/tpm/findOwnCollegeCourse_JiCourse.action"

        try:
            response = self.session.post(url, json={})
            response.raise_for_status()
            data = response.json()

            if data.get("success") and "data" in data and "courses" in data["data"]:
                # 将课程列表转换为courseId索引的字典以便快速查找
                return {
                    course.get("courseId"): course for course in data["data"]["courses"]
                }
            return {}
        except Exception:
            # 出错时返回空字典，不影响主流程
            return {}

    def _get_prerequisites(self):
        """
        获取先修课程数据（第三个数据源）
        
        从先修课程API获取所有课程的先修要求。
        这个API返回的数据包含：
        - 课程ID和对应的先修课程ID
        - 先修课程的逻辑关系（AND、OR等）
        - 先修要求的详细描述（prerequisiteRuleDesc）
        
        Returns:
            dict: 以courseId为键的先修课程列表字典
                每个值是一个列表，包含该课程的所有先修要求项
        """
        url = f"{BASE_URL}/tpm/findAll_PrerequisiteCourse.action"

        try:
            # 添加时间戳参数防止缓存
            response = self.session.post(url, params={"_t": int(time.time() * 1000)})
            response.raise_for_status()
            data = response.json()

            # 调试信息：记录API响应状态
            print(f"[DEBUG] Prerequisites API response: success={data.get('success')}")
            print(
                f"[DEBUG] Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}"
            )

            if data.get("success") and "data" in data:
                raw_prereqs = data["data"]
                print(f"[DEBUG] Raw prerequisites data: {len(raw_prereqs)} items")

                # 显示第一个先修要求的结构作为调试信息
                if raw_prereqs and len(raw_prereqs) > 0:
                    print(f"[DEBUG] First prerequisite item: {raw_prereqs[0]}")

                # 按courseId分组先修课程数据，这样可以快速查找每个课程的所有先修要求
                prereqs = defaultdict(list)
                for item in raw_prereqs:
                    course_id = item.get("courseId")
                    if course_id:
                        prereqs[course_id].append(item)

                print(
                    f"[DEBUG] Grouped prerequisites: {len(prereqs)} course IDs have prereqs"
                )
                return prereqs
            else:
                print("[DEBUG] Prerequisites API failed or no data")
                return {}
        except Exception as e:
            print(f"[DEBUG] Prerequisites API error: {str(e)}")
            return {}

    def _integrate_course_data(self, courses_data, course_details, prerequisites):
        """
        整合多个数据源的课程信息
        
        将三个不同API获取的数据进行整合，生成完整的课程信息：
        1. courses_data: 选课任务数据（主要数据源）
        2. course_details: 课程目录数据（补充描述等信息）
        3. prerequisites: 先修课程数据（先修要求）
        
        数据整合策略：
        - 以课程代码为主键进行分组
        - 合并同一课程的不同section信息
        - 优先使用更完整的数据字段
        - 为每个课程匹配对应的先修要求
        
        Args:
            courses_data (list): 选课任务数据列表
            course_details (dict): 课程详情字典，以courseId为键
            prerequisites (dict): 先修课程字典，以courseId为键
            
        Returns:
            list: 整合后的课程信息列表
        """
        print(
            f"[DEBUG] Starting integration with {len(courses_data)} courses, {len(prerequisites)} prereq groups"
        )

        # 按课程代码分组：同一门课程可能有多个section
        courses_by_code = defaultdict(list)
        for course in courses_data:
            course_code = course.get("courseCode")
            if course_code:
                courses_by_code[course_code].append(course)

        integrated_courses = []
        courses_with_prereqs = 0

        # 遍历每个课程代码，整合数据
        for course_code, course_list in courses_by_code.items():
            # 合并同课程的不同section（主要是合并教师信息）
            merged = self._merge_course_sections(course_list)
            if not merged:
                continue

            # 获取课程ID并查找对应的详细信息和先修要求
            course_id = merged.get("courseId")
            catalog_info = course_details.get(course_id, {})
            prereq_info = prerequisites.get(course_id, [])

            # 统计有先修要求的课程数量（用于调试）
            if prereq_info:
                courses_with_prereqs += 1
                print(
                    f"[DEBUG] Course {course_code} (ID: {course_id}) has {len(prereq_info)} prereqs"
                )

            # 构建最终的课程数据记录
            course_data = self._build_course_record(
                course_code, merged, catalog_info, prereq_info
            )

            if course_data:
                integrated_courses.append(course_data)

        print(
            f"[DEBUG] Integration complete: {courses_with_prereqs} courses have prerequisites"
        )
        return integrated_courses

    def _merge_course_sections(self, course_list):
        """
        合并同一课程的不同section信息
        
        同一门课程可能有多个section（如不同时间的讲座、实验课等），
        需要将它们的信息合并，特别是教师信息。
        
        Args:
            course_list (list): 同一课程的section列表
            
        Returns:
            dict: 合并后的课程信息，包含所有section的教师信息
        """
        if not course_list:
            return {}

        # 以第一个section为基础进行合并
        merged = course_list[0].copy()
        all_instructors = set()

        # 收集所有section的教师信息
        for course in course_list:
            teachers = course.get("lessonTaskTeam", "")
            if teachers:
                # 处理多种分隔符（中英文逗号、分号等）
                for teacher in re.split(r"[,;，；、]", teachers):
                    if teacher.strip():
                        all_instructors.add(teacher.strip())

        # 将所有教师信息存储到合并后的课程数据中
        merged["all_instructors"] = list(all_instructors)
        return merged

    def _build_course_record(self, course_code, main_data, catalog_data, prereq_data):
        """
        构建标准格式的课程记录
        
        将来自不同数据源的课程信息整合成统一的格式。
        数据优先级：main_data > catalog_data（优先使用主数据源）
        
        Args:
            course_code (str): 课程代码（如 "ECE2150J"）
            main_data (dict): 选课任务数据（主数据源）
            catalog_data (dict): 课程目录数据（补充数据源）
            prereq_data (list): 先修课程数据列表
            
        Returns:
            dict: 标准化的课程记录，如果数据无效则返回None
        """
        # 1. 提取并验证课程标题
        course_title = self._extract_course_title(main_data, catalog_data)
        if not course_title:
            return None

        # 2. 解析课程代码中的院系和编号信息
        department, number = self._parse_course_code(course_code)
        
        # 3. 提取学分信息
        course_credits = self._extract_course_credits(main_data, catalog_data)
        
        # 4. 构建先修课程字符串
        prerequisites = self._build_prerequisites_string(course_code, prereq_data)
        
        # 5. 提取课程描述
        description = self._extract_description(main_data, catalog_data)
        
        # 6. 整合教师信息
        instructors = self._extract_instructors(main_data, catalog_data)
        
        # 7. 构建课程URL
        course_url = self._build_course_url(main_data)

        return {
            "course_code": course_code,
            "course_title": course_title,
            "department": department,
            "number": number,
            "course_credits": course_credits,
            "pre_requisites": prerequisites,
            "description": description,
            "course_topics": [],  # 暂时为空，保持接口一致
            "instructors": instructors,
            "url": course_url,
        }
    
    def _extract_course_title(self, main_data, catalog_data):
        """提取课程标题（优先使用英文名称）"""
        return (
            main_data.get("courseNameEn", "")
            or main_data.get("courseName", "")
            or catalog_data.get("courseNameEn", "")
            or catalog_data.get("courseName", "")
        ).strip()
    
    def _parse_course_code(self, course_code):
        """从课程代码中解析院系和编号"""
        department = ""
        number = 0
        
        if course_code:
            # 提取院系代码（字母部分）
            dept_match = re.match(r"^([A-Z]+)", course_code)
            if dept_match:
                department = dept_match.group(1)

            # 提取课程编号（数字部分）
            num_match = re.search(r"(\d+)", course_code)
            if num_match:
                number = int(num_match.group(1))
                
        return department, number
    
    def _extract_course_credits(self, main_data, catalog_data):
        """提取课程学分信息"""
        course_credits = main_data.get("totalCredit", 0) or catalog_data.get("credit", 0)
        
        if isinstance(course_credits, str):
            try:
                course_credits = int(float(course_credits))
            except (ValueError, TypeError):
                course_credits = 0
                
        return course_credits
    
    def _build_prerequisites_string(self, course_code, prereq_data):
        """构建先修课程字符串"""
        if not prereq_data:
            return ""
            
        print(
            f"[DEBUG] Building prerequisites for {course_code}, prereq_data has {len(prereq_data)} items"
        )
        
        prereq_codes = []
        for item in prereq_data:
            rule_desc = item.get("prerequisiteRuleDesc", "")
            print(f"[DEBUG] Processing prerequisite rule: {rule_desc}")

            if rule_desc:
                # 使用完整的规则描述
                prereq_codes.append(rule_desc)

        if prereq_codes:
            prerequisites = " || ".join(prereq_codes)
            print(f"[DEBUG] Final prerequisites for {course_code}: {prerequisites}")
            return prerequisites
            
        return ""
    
    def _extract_description(self, main_data, catalog_data):
        """提取课程描述信息"""
        return (
            main_data.get("description", "")
            or catalog_data.get("description", "")
            or main_data.get("memo", "")
            or catalog_data.get("memo", "")
        ).strip()
    
    def _extract_instructors(self, main_data, catalog_data):
        """整合教师信息"""
        instructors = main_data.get("all_instructors", [])
        teacher_name = catalog_data.get("teacherName", "")
        
        if teacher_name:
            # 处理目录数据中的教师信息
            for teacher in re.split(r"[,;，；、]", teacher_name):
                if teacher.strip() and teacher.strip() not in instructors:
                    instructors.append(teacher.strip())
                    
        return instructors
    
    def _build_course_url(self, main_data):
        """构建课程详情页面URL"""
        course_id = main_data.get("courseId")
        return f"{COURSE_DETAIL_URL_PREFIX}{course_id}" if course_id else ""


# ============================================================================
# 向后兼容性函数
# 这些函数保持与旧版本爬虫的接口兼容，确保现有代码不会中断
# ============================================================================

# 全局爬虫实例（单例模式）
_crawler = None


def _get_crawler():
    """
    获取爬虫实例（单例模式）
    
    使用单例模式确保整个应用中只有一个爬虫实例，
    避免重复初始化和多余的网络连接。
    
    Returns:
        CourseSelCrawler: 爬虫实例
    """
    global _crawler
    if _crawler is None:
        _crawler = CourseSelCrawler()
    return _crawler


def crawl_program_urls():
    """
    获取所有课程URL（兼容性接口）
    
    这是旧版本爬虫的主要接口，现在内部使用新的API爬虫。
    为了保持向后兼容性，该函数仍然返回课程URL列表，
    但同时会缓存完整的课程数据供其他函数使用。
    
    Returns:
        list: 课程URL列表
    """
    crawler = _get_crawler()
    courses = crawler.get_all_courses()

    # 提取课程URL列表以保持接口兼容性
    course_urls = []
    for course in courses:
        if course.get("url"):
            course_urls.append(course["url"])

    # 将完整的课程数据缓存起来，供 _crawl_course_data 函数使用
    # 这样避免了重复的网络请求
    if not hasattr(crawl_program_urls, "_course_data_cache"):
        crawl_program_urls._course_data_cache = {}

    for course in courses:
        if course.get("url"):
            crawl_program_urls._course_data_cache[course["url"]] = course

    return course_urls


def _get_department_urls_from_url(_):
    """
    兼容性函数：从URL获取部门课程URL
    
    注意：由于新的API架构，这个函数实际上直接调用主爬取函数。
    参数被忽略，因为新的API不需要基于URL进行增量爬取。
    
    Returns:
        list: 课程URL列表
    """
    return crawl_program_urls()


def _is_department_url(candidate_url):
    """
    检查URL是否为有效的课程详情URL
    
    Args:
        candidate_url (str): 候选URL
        
    Returns:
        bool: 如果URL匹配课程详情页面格式则返回True
    """
    return candidate_url.startswith(COURSE_DETAIL_URL_PREFIX)


def _crawl_course_data(course_url):
    """
    爬取单个课程数据（兼容性接口）
    
    在新架构中，我们一次性获取所有课程数据并缓存，
    所以这个函数直接从缓存中返回数据，不进行实际的网络请求。
    
    Args:
        course_url (str): 课程详情页面URL
        
    Returns:
        dict: 课程数据字典，如果未找到则返回空字典
    """
    # 从缓存中获取课程数据
    if hasattr(crawl_program_urls, "_course_data_cache"):
        course_data = crawl_program_urls._course_data_cache.get(course_url)
        if course_data:
            return course_data

    # 如果缓存中没有找到数据，返回空字典
    return {}


def import_department(department_data):
    """
    将课程数据导入数据库
    
    这个函数负责将爬取的课程数据保存到Django数据库中。
    处理课程、教师和课程开设信息的创建和更新。
    
    Args:
        department_data (list): 课程数据列表，每个元素是课程信息字典
    """
    for course_data in department_data:
        # 使用 update_or_create 确保数据的幂等性
        # 如果课程已存在则更新，否则创建新记录
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
                # 注意：source字段在当前模型中不存在，已移除
            },
        )

        # 处理教师信息
        if "instructors" in course_data and course_data["instructors"]:
            for instructor_name in course_data["instructors"]:
                # 获取或创建教师记录
                instructor, _ = Instructor.objects.get_or_create(name=instructor_name)
                
                # 为当前学期创建课程开设记录（如果不存在）
                offering, _ = CourseOffering.objects.get_or_create(
                    course=course,
                    term=CURRENT_TERM,
                    defaults={"section": 1, "period": ""},
                )
                # 将教师关联到课程开设记录
                offering.instructors.add(instructor)


def extract_prerequisites(pre_requisites):
    """
    处理先修课程字符串格式（兼容性函数）
    
    这个函数对先修课程字符串进行标准化处理，
    统一格式和术语，使其更适合在系统中使用。
    
    Args:
        pre_requisites (str): 原始先修课程字符串
        
    Returns:
        str: 处理后的先修课程字符串
    """
    result = pre_requisites

    # 移除前缀标识
    result = result.replace("Pre-requisites:", "").strip()

    # 标准化学分要求术语
    result = result.replace("Obtained Credit", "obtained_credit").strip()
    result = result.replace("Credits Submitted", "credits_submitted").strip()

    # 标准化逻辑运算符格式（添加空格以提高可读性）
    result = result.replace("&&", " && ").strip()
    result = result.replace("||", " || ").strip()

    return result
