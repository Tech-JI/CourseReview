"""
Unified spider data management system
Provides interactive cache management, crawler execution, and data import functionality
"""

import json
import os
import sys
import django
import asyncio
from datetime import datetime
from pathlib import Path

# Setup Django environment
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django.setup()


class CrawlerManager:
    """
    Unified crawler management system

    Coordinates between different crawler components and provides
    a clean interface for data extraction and integration.
    """

    def __init__(self, cache_dir=None):
        self.cache = CourseDataCache(cache_dir)
        self.config = None
        self.api_crawler = None
        self.website_crawler = None
        self.integrator = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize crawler components with lazy loading"""
        try:
            from apps.spider.crawlers.orc import (
                CrawlerConfig,
                CourseSelAPICrawler,
                OfficialWebsiteCrawler,
                CourseDataIntegrator,
            )

            self.config = CrawlerConfig()
            self.website_crawler = OfficialWebsiteCrawler()
            self.integrator = CourseDataIntegrator()
        except ImportError as e:
            print(f"Warning: Could not import crawler components: {e}")

    def create_api_crawler(self, jsessionid):
        """Create API crawler with authentication"""
        try:
            from apps.spider.crawlers.orc import CourseSelAPICrawler

            self.api_crawler = CourseSelAPICrawler(jsessionid)
            return self.api_crawler
        except ImportError as e:
            print(f"Error: Could not import CourseSelAPICrawler: {e}")
            return None

    def crawl_coursesel_data(self, jsessionid, apis=None):
        """
        Crawl data from course selection system

        Args:
            jsessionid: Authentication session ID
            apis: List of APIs to crawl ('lesson_tasks', 'course_catalog', 'prerequisites')
                 If None, crawls all APIs

        Returns:
            dict: Dictionary with crawled data
        """
        if apis is None:
            apis = ["lesson_tasks", "course_catalog", "prerequisites"]

        api_crawler = self.create_api_crawler(jsessionid)
        if not api_crawler:
            return {}

        results = {}

        try:
            if "lesson_tasks" in apis:
                print("[*] Crawling lesson tasks...")
                results["lesson_tasks"] = api_crawler.crawl_lesson_tasks()
                print(f"[+] Retrieved {len(results['lesson_tasks'])} lesson tasks")

            if "course_catalog" in apis:
                print("[*] Crawling course catalog...")
                results["course_catalog"] = api_crawler.crawl_course_catalog()
                print(
                    f"[+] Retrieved {len(results['course_catalog'])} courses from catalog"
                )

            if "prerequisites" in apis:
                print("[*] Crawling prerequisites...")
                results["prerequisites"] = api_crawler.crawl_prerequisites()
                print(
                    f"[+] Retrieved prerequisites for {len(results['prerequisites'])} courses"
                )

            # Save to cache
            if results:
                saved_files = self.cache.save_coursesel_data(
                    results.get("lesson_tasks"),
                    results.get("course_catalog"),
                    results.get("prerequisites"),
                )
                print(f"[+] Saved {len(saved_files)} cache files")

            return results

        except Exception as e:
            print(f"[-] Course selection crawling failed: {e}")
            return {}

    def crawl_official_data(self):
        """
        Crawl data from official website

        Returns:
            dict: Dictionary with official website data
        """
        if not self.website_crawler:
            print("[-] Official website crawler not available")
            return {}

        try:
            print("[*] Crawling official website...")
            official_data = asyncio.run(self.website_crawler.crawl_official_data())
            print(f"[+] Retrieved {len(official_data)} courses from official website")

            # Convert to list format and save to cache
            if official_data:
                official_list = []
                for course_code, course_info in official_data.items():
                    course_info["course_code"] = course_code
                    official_list.append(course_info)

                filepath = self.cache.save_to_jsonl(official_list, "official")
                print(f"[+] Saved to cache: {Path(filepath).name}")

            return official_data

        except Exception as e:
            print(f"[-] Official website crawling failed: {e}")
            return {}

    def integrate_and_import_data(self, import_to_db=True):
        """
        Integrate cached data and optionally import to database

        Args:
            import_to_db: Whether to import integrated data to database

        Returns:
            dict: Integration and import results
        """
        if not self.integrator:
            print("[-] Data integrator not available")
            return {}

        # Load cached data
        cached_data = self._load_cached_data()
        if not any(cached_data.values()):
            print("[-] No cached data found to integrate")
            return {}

        try:
            # Integrate data
            print("[*] Integrating data...")
            integrated_data = self.integrator.integrate_data(
                cached_data["lesson_tasks"],
                cached_data["course_catalog"],
                cached_data["prerequisites"],
                cached_data["official_data"],
            )

            print(f"[+] Integrated {len(integrated_data)} course records")

            # Save integrated data
            if integrated_data:
                filepath = self.cache.save_to_jsonl(integrated_data, "integrated")
                print(f"[+] Saved integrated data: {Path(filepath).name}")

            # Import to database if requested
            results = {"integrated_count": len(integrated_data)}
            if import_to_db and integrated_data:
                print("[*] Importing to database...")
                import_results = self._import_to_database(integrated_data)
                results.update(import_results)

            return results

        except Exception as e:
            print(f"[-] Integration failed: {e}")
            return {}

    def _load_cached_data(self):
        """Load data from cache files"""
        files = self.cache.list_cache_files()

        data = {
            "lesson_tasks": [],
            "course_catalog": {},
            "prerequisites": {},
            "official_data": {},
        }

        for filepath in files:
            filename = filepath.name
            file_data = self.cache.load_data_file(filepath)

            if "coursesel_lesson_tasks" in filename:
                data["lesson_tasks"] = file_data
            elif "coursesel_course_catalog" in filename:
                data["course_catalog"] = {
                    item.get("courseId"): item
                    for item in file_data
                    if item.get("courseId")
                }
            elif "coursesel_prerequisites" in filename:
                from collections import defaultdict

                prerequisites = defaultdict(list)
                for item in file_data:
                    course_id = item.get("courseId")
                    if course_id:
                        prerequisites[course_id].append(item)
                data["prerequisites"] = prerequisites
            elif "official" in filename:
                for item in file_data:
                    course_code = item.get("course_code")
                    if course_code:
                        data["official_data"][course_code] = item

        return data

    def _import_to_database(self, integrated_data):
        """Import integrated data to database"""
        try:
            # Import the database models
            from apps.web.models import Course, CourseOffering, Instructor
            from lib.constants import CURRENT_TERM

            success_count = 0
            error_count = 0

            for course_data in integrated_data:
                try:
                    # Create or update course
                    course_defaults = {
                        "course_title": course_data.get("course_title", ""),
                        "course_credits": course_data.get("course_credits", 0),
                        "pre_requisites": course_data.get("pre_requisites", ""),
                        "description": course_data.get("description", ""),
                        "url": course_data.get("url", ""),
                        "department": course_data.get("department", ""),
                        "number": course_data.get("number", 0),
                    }

                    course, _ = Course.objects.update_or_create(
                        course_code=course_data.get("course_code", ""),
                        defaults=course_defaults,
                    )

                    # Handle instructors
                    instructors = course_data.get("instructors", [])
                    if instructors:
                        course_offering, _ = CourseOffering.objects.get_or_create(
                            course=course, term=CURRENT_TERM
                        )

                        for instructor_name in instructors:
                            if instructor_name.strip():
                                instructor, _ = Instructor.objects.get_or_create(
                                    name=instructor_name.strip()
                                )
                                course_offering.instructors.add(instructor)

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    print(
                        f"[-] Error importing {course_data.get('course_code', 'Unknown')}: {e}"
                    )

            return {
                "success": success_count,
                "errors": error_count,
                "total": success_count + error_count,
            }

        except ImportError as e:
            print(f"[-] Database import failed - missing dependencies: {e}")
            return {
                "success": 0,
                "errors": len(integrated_data),
                "total": len(integrated_data),
            }
        except Exception as e:
            print(f"[-] Database import failed: {e}")
            return {
                "success": 0,
                "errors": len(integrated_data),
                "total": len(integrated_data),
            }


class CourseDataCache:
    """Course data cache manager"""

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            # Default to the new cache directory location
            cache_dir = Path(__file__).parent / "crawlers" / "data_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def save_to_json(self, data, data_type):
        """Save data to json file with overwrite (no timestamp)"""
        filename = f"{data_type}.json"
        filepath = self.cache_dir / filename

        print(f"Saving data to: {filepath}")
        print(f"Data count: {len(data) if isinstance(data, list) else 1}")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Data saved to: {filepath}")
        return filepath

    def save_to_jsonl(self, data, data_type):
        """Save data to jsonl file with overwrite (no timestamp)"""
        filename = f"{data_type}.jsonl"
        filepath = self.cache_dir / filename

        print(f"Saving data to: {filepath}")
        print(f"Data count: {len(data) if isinstance(data, list) else 1}")

        with open(filepath, "w", encoding="utf-8") as f:
            if isinstance(data, list):
                for item in data:
                    json.dump(item, f, ensure_ascii=False)
                    f.write("\n")
            else:
                json.dump(data, f, ensure_ascii=False)
                f.write("\n")

        print(f"Data saved to: {filepath}")
        return filepath

    def save_coursesel_data(self, lesson_tasks, course_catalog, prerequisites):
        """Save course selection system data to separate files with overwrite"""
        saved_files = {}

        # Save lesson tasks data as JSON
        if lesson_tasks:
            filepath = self.save_to_json(lesson_tasks, "coursesel_lesson_tasks")
            saved_files["lesson_tasks"] = filepath

        # Save course catalog data as JSONL
        if course_catalog:
            # Convert dict to list for consistent format
            catalog_list = (
                list(course_catalog.values())
                if isinstance(course_catalog, dict)
                else course_catalog
            )
            filepath = self.save_to_jsonl(catalog_list, "coursesel_course_catalog")
            saved_files["course_catalog"] = filepath

        # Save prerequisites data as JSONL
        if prerequisites:
            # Convert defaultdict to regular dict, then to list
            prereq_list = []
            for course_id, prereq_items in prerequisites.items():
                for item in prereq_items:
                    prereq_list.append(item)
            filepath = self.save_to_jsonl(prereq_list, "coursesel_prerequisites")
            saved_files["prerequisites"] = filepath

        return saved_files

    def load_from_json(self, filepath):
        """Load data from json file"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_from_jsonl(self, filepath):
        """Load data from jsonl file"""
        data = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def load_data_file(self, filepath):
        """Load data from either JSON or JSONL file based on extension"""
        if filepath.suffix.lower() == ".json":
            return self.load_from_json(filepath)
        elif filepath.suffix.lower() == ".jsonl":
            return self.load_from_jsonl(filepath)
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")

    def list_cache_files(self):
        """List all cache files (both .json and .jsonl)"""
        files = list(self.cache_dir.glob("*.jsonl")) + list(
            self.cache_dir.glob("*.json")
        )
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files

    def get_cache_info(self, filepath):
        """Get cache file information"""
        stat = filepath.stat()
        data = self.load_data_file(filepath)

        return {
            "filename": filepath.name,
            "path": str(filepath),
            "size": f"{stat.st_size / 1024:.1f} KB",
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "count": len(data),
            "preview": data[:3] if len(data) > 3 else data,  # Preview first 3 items
        }


def interactive_cache_manager():
    """Interactive cache manager"""
    cache = CourseDataCache()

    print("=" * 60)
    print("Course Data Cache Manager")
    print("=" * 60)

    files = cache.list_cache_files()

    if not files:
        print("No cache files found")
        print("Please run the crawler first to generate data cache")
        return None

    print(f"Found {len(files)} cache files:")
    print()

    for i, filepath in enumerate(files, 1):
        info = cache.get_cache_info(filepath)
        print(f"{i}. {info['filename']}")
        print(f"   Modified: {info['modified']}")
        print(f"   File size: {info['size']}")
        print(f"   Data count: {info['count']}")

        if info["preview"]:
            print("   Data preview:")
            for j, item in enumerate(info["preview"]):
                course_code = item.get("course_code", "N/A")
                course_title = item.get("course_title", "N/A")
                print(f"      {j + 1}. {course_code}: {course_title}")
        print()

    while True:
        try:
            choice = input(
                f"Select file to import (1-{len(files)}) or 'q' to quit: "
            ).strip()

            if choice.lower() == "q":
                print("Exiting cache manager")
                return None

            file_index = int(choice) - 1
            if 0 <= file_index < len(files):
                selected_file = files[file_index]
                print(f"Selected file: {selected_file.name}")
                return selected_file
            else:
                print(f"Please enter a number between 1-{len(files)}")

        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nExiting cache manager")
            return None


def preview_data_before_import(filepath, limit=10):
    """Preview data before import"""
    cache = CourseDataCache()
    data = cache.load_data_file(filepath)

    print("=" * 60)
    print(f"Data Preview ({filepath.name})")
    print("=" * 60)
    print(f"Total data count: {len(data)}")
    print(f"Previewing first {min(limit, len(data))} items:")
    print()

    for i, item in enumerate(data[:limit], 1):
        print(f"{i}. Course code: {item.get('course_code', 'N/A')}")
        print(f"   Course title: {item.get('course_title', 'N/A')}")
        print(f"   Credits: {item.get('course_credits', 'N/A')}")
        print(f"   Department: {item.get('department', 'N/A')}")
        print(f"   Description length: {len(item.get('description', ''))}")
        print(f"   Instructors: {', '.join(item.get('instructors', []))}")
        print()

    if len(data) > limit:
        print(f"... and {len(data) - limit} more items")

    print("=" * 60)

    while True:
        try:
            confirm = (
                input("Confirm import these data to database? (y/n): ").strip().lower()
            )
            if confirm in ["y", "yes"]:
                return True
            elif confirm in ["n", "no"]:
                return False
            else:
                print("Please enter y or n")
        except KeyboardInterrupt:
            print("\nImport cancelled")
            return False


def main_menu():
    """Main interactive menu for spider data management"""
    print("\n" + "=" * 60)
    print("Spider Data Management System")
    print("=" * 60)
    print("1. Run Crawler (Fetch new data)")
    print("2. Manage Cache Files")
    print("3. Import from Cache to Database")
    print("4. Clean Cache Files")
    print("5. Exit")
    print("=" * 60)

    while True:
        try:
            choice = input("Select operation (1-5): ").strip()

            if choice == "1":
                run_crawler()
            elif choice == "2":
                manage_cache()
            elif choice == "3":
                import_from_cache()
            elif choice == "4":
                clean_cache()
            elif choice == "5":
                print("Goodbye!")
                break
            else:
                print("Please enter a number between 1-5")

        except (ValueError, KeyboardInterrupt):
            print("\nProgram interrupted")
            break
        except Exception as e:
            print(f"Error occurred: {str(e)}")


def run_crawler():
    """Run crawler to fetch new data"""
    print("\n" + "=" * 60)
    print("Run Crawler")
    print("=" * 60)

    try:
        manager = CrawlerManager()

        # Get JSESSIONID for course selection system
        print("Course Selection System requires authentication.")
        print("Please enter your JSESSIONID cookie:")
        jsessionid = input("JSESSIONID: ").strip()

        if jsessionid:
            # Crawl course selection data
            manager.crawl_coursesel_data(jsessionid)
            print("Course selection crawling completed")

        # Crawl official website data
        manager.crawl_official_data()
        print("Official website crawling completed")

        # Integrate and import data
        results = manager.integrate_and_import_data(import_to_db=True)
        print(f"Data integration and import completed: {results}")

    except Exception as e:
        print(f"Crawler execution failed: {str(e)}")


def manage_cache():
    """Manage and view cache files"""
    print("\n" + "=" * 60)
    print("Manage Cache Files")
    print("=" * 60)

    cache = CourseDataCache()
    files = cache.list_cache_files()

    if not files:
        print("No cache files found")
        return

    print(f"Found {len(files)} cache files:")

    for i, filepath in enumerate(files, 1):
        info = cache.get_cache_info(filepath)
        print(f"\n{i}. {info['filename']}")
        print(f"   Modified: {info['modified']}")
        print(f"   Size: {info['size']}")
        print(f"   Count: {info['count']}")

        # Show preview
        if info["preview"]:
            print("   Preview:")
            for j, item in enumerate(info["preview"]):
                course_code = item.get("course_code", "N/A")
                course_title = item.get("course_title", "N/A")
                print(f"      {j + 1}. {course_code}: {course_title}")


def import_from_cache():
    """Import data from cache to database"""
    print("\n" + "=" * 60)
    print("Import from Cache")
    print("=" * 60)

    selected_file = interactive_cache_manager()
    if not selected_file:
        return

    try:
        cache = CourseDataCache()
        data = cache.load_data_file(selected_file)

        # Preview and confirm import
        if preview_data_before_import(selected_file, limit=10):
            print("Starting database import...")

            # Use CrawlerManager for database import
            manager = CrawlerManager()

            # Check if this is integrated data or needs integration
            if "integrated" in selected_file.name:
                # Direct import of integrated data
                result = manager._import_to_database(data)
            else:
                # Single file data needs integration first
                print("Single file detected, integrating with other cached data...")
                result = manager.integrate_and_import_data(import_to_db=True)

            print("\nImport completed!")
            print(f"Success: {result.get('success', 0)} items")
            print(f"Failed: {result.get('errors', 0)} items")

        else:
            print("Import cancelled")

    except Exception as e:
        print(f"Error during import process: {str(e)}")


def clean_cache():
    """Clean cache files"""
    print("\n" + "=" * 60)
    print("Clean Cache Files")
    print("=" * 60)

    cache = CourseDataCache()
    files = cache.list_cache_files()

    if not files:
        print("No cache files found")
        return

    print(f"Found {len(files)} cache files")

    choice = input("Delete all cache files? (y/n): ").strip().lower()

    if choice in ["y", "yes"]:
        deleted_count = 0
        for filepath in files:
            try:
                filepath.unlink()
                deleted_count += 1
                print(f"Deleted: {filepath.name}")
            except Exception as e:
                print(f"Failed to delete {filepath.name}: {str(e)}")

        print(f"Cleanup completed, deleted {deleted_count} files")
    else:
        print("Cleanup cancelled")


def interactive_spider_manager():
    """Interactive spider management system"""
    print("=" * 60)
    print("Interactive Spider Management System")
    print("=" * 60)

    cache = CourseDataCache()

    while True:
        print("\n1. Crawl data from websites")
        print("2. Import data from cache files")
        print("3. View cache files")
        print("4. Clean cache files")
        print("5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            # Crawling workflow
            crawl_workflow(cache)
        elif choice == "2":
            # Import workflow
            import_workflow(cache)
        elif choice == "3":
            # View cache files
            interactive_cache_manager()
        elif choice == "4":
            # Clean cache files
            clean_cache()
        elif choice == "5":
            print("Exiting...")
            break
        else:
            print("Invalid choice, please try again")


def crawl_workflow(cache):
    """Crawling workflow"""
    print("\n" + "=" * 40)
    print("Data Crawling Workflow")
    print("=" * 40)

    print("\nAvailable data sources:")
    print("1. Course Selection System (coursesel.umji.sjtu.edu.cn)")
    print("2. Official Website (ji.sjtu.edu.cn)")
    print("3. Both")

    source_choice = input("\nSelect data source (1-3): ").strip()

    if source_choice == "1":
        crawl_coursesel_workflow(cache)
    elif source_choice == "2":
        crawl_official_workflow(cache)
    elif source_choice == "3":
        crawl_coursesel_workflow(cache)
        print("\n" + "-" * 40)
        crawl_official_workflow(cache)
    else:
        print("Invalid choice")


def crawl_coursesel_workflow(cache):
    """Course selection system crawling workflow"""
    print("\n" + "=" * 40)
    print("Course Selection System Crawling")
    print("=" * 40)

    # Request JSESSIONID first since all coursesel APIs need authentication
    print("\nCourse Selection System requires authentication.")
    print("Please enter your JSESSIONID cookie:")
    print("(Found in browser dev tools under Network or Application tabs)")
    jsessionid = input("JSESSIONID: ").strip()

    if not jsessionid:
        print("JSESSIONID cannot be empty. Cancelling course selection crawling.")
        return

    print("\nAvailable APIs:")
    print("1. Lesson Tasks")
    print("2. Course Catalog")
    print("3. Prerequisites")
    print("4. All APIs")
    print("\nYou can select multiple APIs by entering numbers separated by commas")
    print("For example: 1,2 for Lesson Tasks and Course Catalog")

    api_choice = input(
        "\nSelect APIs to crawl (1-4 or combinations like 1,2,3): "
    ).strip()

    # Parse user input to determine which APIs to crawl
    selected_apis = set()

    if api_choice == "4":
        selected_apis = {"1", "2", "3"}
    else:
        # Split by comma (both English and Chinese commas) and clean up
        api_choice = api_choice.replace(
            ",", ","
        )  # Replace Chinese comma with English comma
        choices = [choice.strip() for choice in api_choice.split(",")]
        for choice in choices:
            if choice in ["1", "2", "3"]:
                selected_apis.add(choice)
            else:
                print(f"Invalid choice '{choice}', skipping...")

    if not selected_apis:
        print("No valid APIs selected")
        return

    print(f"\nSelected APIs: {', '.join(sorted(selected_apis))}")

    # Map choices to API names
    api_mapping = {"1": "lesson_tasks", "2": "course_catalog", "3": "prerequisites"}

    apis_to_crawl = [
        api_mapping[choice] for choice in selected_apis if choice in api_mapping
    ]

    try:
        # Use CrawlerManager for organized crawling
        manager = CrawlerManager(cache.cache_dir)
        results = manager.crawl_coursesel_data(jsessionid, apis_to_crawl)

        if results:
            print(f"\n[+] Successfully crawled {len(results)} API endpoints")
            for api_name, data in results.items():
                print(f"  - {api_name}: {len(data) if data else 0} records")
        else:
            print("[-] No data was crawled")

    except Exception as e:
        print(f"[-] Crawling failed: {str(e)}")
        import traceback

        traceback.print_exc()


def crawl_official_workflow(cache):
    """Official website crawling workflow"""
    print("\n" + "=" * 40)
    print("Official Website Crawling")
    print("=" * 40)

    print("\n[*] Crawling official website data...")

    try:
        # Use CrawlerManager for organized crawling
        manager = CrawlerManager(cache.cache_dir)
        official_data = manager.crawl_official_data()

        if official_data:
            print(
                f"[+] Successfully crawled {len(official_data)} courses from official website"
            )
        else:
            print("[-] No data was crawled from official website")

    except Exception as e:
        print(f"[-] Official website crawling failed: {str(e)}")
        import traceback

        traceback.print_exc()


def import_workflow(cache):
    """Data import workflow"""
    print("\n" + "=" * 40)
    print("Data Import Workflow")
    print("=" * 40)

    files = cache.list_cache_files()

    if not files:
        print("No cache files found. Please crawl data first.")
        return

    print(f"\nFound {len(files)} cache files:")

    # Group files by type
    file_groups = {}
    for i, filepath in enumerate(files):
        filename = filepath.name
        if "coursesel_lesson_tasks" in filename:
            file_type = "Lesson Tasks"
        elif "coursesel_course_catalog" in filename:
            file_type = "Course Catalog"
        elif "coursesel_prerequisites" in filename:
            file_type = "Prerequisites"
        elif "official" in filename:
            file_type = "Official Website"
        else:
            file_type = "Integrated"

        if file_type not in file_groups:
            file_groups[file_type] = []
        file_groups[file_type].append((i, filepath))

    # Display grouped files
    for file_type, file_list in file_groups.items():
        print(f"\n{file_type}:")
        for i, filepath in file_list:
            info = cache.get_cache_info(filepath)
            print(
                f"  {i + 1:2d}. {info['filename']} ({info['size']}, {info['count']} records, {info['modified']})"
            )

    print(f"\n{len(files) + 1}. Import and integrate data")

    choice = input(f"\nSelect file to view or import (1-{len(files) + 1}): ").strip()

    try:
        choice_num = int(choice)
        if 1 <= choice_num <= len(files):
            # View file details
            filepath = files[choice_num - 1]
            info = cache.get_cache_info(filepath)
            print(f"\nFile details: {info['filename']}")
            print(f"Size: {info['size']}")
            print(f"Records: {info['count']}")
            print(f"Modified: {info['modified']}")
            print("Preview:")
            for i, item in enumerate(info["preview"]):
                print(
                    f"  Record {i + 1}: {json.dumps(item, ensure_ascii=False, indent=2)[:200]}..."
                )

        elif choice_num == len(files) + 1:
            # Import and integrate data
            integrate_and_import_data(cache)
        else:
            print("Invalid choice")

    except ValueError:
        print("Invalid input")


def integrate_and_import_data(cache):
    """Integrate data from multiple cache files and import to database"""
    print("\n" + "=" * 40)
    print("Data Integration and Import")
    print("=" * 40)

    try:
        # Use CrawlerManager for organized integration
        manager = CrawlerManager(cache.cache_dir)

        # Check if we have any cached data
        files = cache.list_cache_files()
        if not files:
            print("[-] No cache files found to integrate")
            return

        print(f"[*] Found {len(files)} cache files")
        for filepath in files:
            print(f"  - {filepath.name}")

        # Integrate and import data
        print("\n[*] Starting integration and import process...")
        results = manager.integrate_and_import_data(import_to_db=True)

        if results:
            print("\n[+] Integration and import completed!")
            print(f"    Integrated courses: {results.get('integrated_count', 0)}")
            if "success" in results:
                print(f"    Database import - Success: {results['success']}")
                print(f"    Database import - Errors: {results['errors']}")
                print(f"    Database import - Total: {results['total']}")
        else:
            print("[-] Integration failed or no data to process")

    except Exception as e:
        print(f"[-] Integration and import failed: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    try:
        interactive_spider_manager()
    except KeyboardInterrupt:
        print("\nProgram exited")
    except Exception as e:
        print(f"Program error: {str(e)}")
