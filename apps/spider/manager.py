"""
Unified spider data management system
Provides interactive cache management, crawler execution, and data import functionality
"""

import json
import os
import sys
import django
from datetime import datetime
from pathlib import Path

# Setup Django environment
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django.setup()


class CourseDataCache:
    """Course data cache manager"""

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            # Default to the new cache directory location
            cache_dir = Path(__file__).parent / "crawlers" / "data_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def save_to_jsonl(self, data, data_type, timestamp=None):
        """Save data to jsonl file"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{data_type}_{timestamp}.jsonl"
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

    def load_from_jsonl(self, filepath):
        """Load data from jsonl file"""
        data = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def list_cache_files(self):
        """List all cache files"""
        files = list(self.cache_dir.glob("*.jsonl"))
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files

    def get_cache_info(self, filepath):
        """Get cache file information"""
        stat = filepath.stat()
        data = self.load_from_jsonl(filepath)

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
    data = cache.load_from_jsonl(filepath)

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
        from apps.spider.crawlers.orc import CourseSelCrawler

        crawler = CourseSelCrawler()
        data = crawler.get_all_courses(use_cache=False, save_cache=True)

        print(f"Crawler execution completed, collected {len(data)} courses")

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
        data = cache.load_from_jsonl(selected_file)

        # Preview and confirm import
        if preview_data_before_import(selected_file, limit=10):
            print("Starting database import...")

            from apps.spider.crawlers.orc import import_department

            # Use batch import and get statistics
            result = import_department(data)

            print("\nImport completed!")
            print(f"Success: {result['success']} items")
            print(f"Failed: {result['errors']} items")

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


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nProgram exited")
    except Exception as e:
        print(f"Program error: {str(e)}")
