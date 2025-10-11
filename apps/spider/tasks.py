# from apps.spider.crawlers import medians, orc, timetable
from celery import shared_task
from django.db import transaction

from apps.spider.models import CrawledData
from lib import task_utils

# from lib.constants import CURRENT_TERM
# from lib.terms import get_next_term


@shared_task
@task_utils.email_if_fails
@transaction.atomic
def import_pending_crawled_data(crawled_data_pk):
    """
    Import pending crawled data to database

    Args:
        crawled_data_pk (int): Primary key of CrawledData record to import
    """
    crawled_data = CrawledData.objects.select_for_update().get(pk=crawled_data_pk)
    # if crawled_data.data_type == CrawledData.MEDIANS:
    #     medians.import_medians(crawled_data.pending_data)
    # elif
    if crawled_data.data_type == CrawledData.ORC_DEPARTMENT_COURSES:
        # Use manager's import functionality
        from apps.spider.manager import CrawlerManager

        manager = CrawlerManager()

        # Import the pending data
        results = manager._import_to_database(crawled_data.pending_data)
        print(f"Import results: {results}")

        # Mark data as current after successful import
        crawled_data.current_data = crawled_data.pending_data
        crawled_data.save()

        return results
    else:
        print(f"Unsupported data type: {crawled_data.data_type}")
        return False


@shared_task
@task_utils.email_if_fails
def crawl_coursesel_data(jsessionid=None):
    """
    Scheduled task to crawl CourseSelection API data

    Args:
        jsessionid (str, optional): Session ID for authentication.
                                   If None, will need to be provided via other means.

    Returns:
        dict: Results of crawling operation
    """
    try:
        from apps.spider.manager import CrawlerManager

        manager = CrawlerManager()

        if not jsessionid:
            # For automated tasks, we might need to handle authentication differently
            # This could be configured via environment variables or settings
            print("Warning: No jsessionid provided for automated crawling")
            return {
                "status": "skipped",
                "message": "No authentication provided for CourseSelection API crawling",
            }

        print("Starting CourseSelection API crawling...")
        coursesel_data = manager.crawl_coursesel_data(jsessionid)

        result = {
            "status": "success",
            "courses_found": len(coursesel_data),
            "message": f"Successfully crawled {len(coursesel_data)} courses from CourseSelection API",
        }
        print(result["message"])
        return result

    except Exception as e:
        error_msg = f"CourseSelection API crawling failed: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}


@shared_task
@task_utils.email_if_fails
def crawl_official_data():
    """
    Scheduled task to crawl official website data

    Returns:
        dict: Results of crawling operation
    """
    try:
        from apps.spider.manager import CrawlerManager

        manager = CrawlerManager()

        print("Starting official website crawling...")
        official_data = manager.crawl_official_data()

        result = {
            "status": "success",
            "courses_found": len(official_data),
            "message": f"Successfully crawled {len(official_data)} courses from official website",
        }
        print(result["message"])
        return result

    except Exception as e:
        error_msg = f"Official website crawling failed: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}


@shared_task
@task_utils.email_if_fails
def integrate_and_import_data():
    """
    Scheduled task to integrate cached data and import to database

    Returns:
        dict: Results of integration and import operation
    """
    try:
        from apps.spider.manager import CrawlerManager

        manager = CrawlerManager()

        print("Starting data integration and import...")
        results = manager.integrate_and_import_data()

        if results:
            result = {
                "status": "success",
                "imported_courses": results.get("success", 0),
                "failed_imports": results.get("errors", 0),
                "total_processed": results.get("total", 0),
                "message": f"Successfully imported {results.get('success', 0)} courses",
            }
        else:
            result = {"status": "warning", "message": "No data to integrate or import"}

        print(result["message"])
        return result

    except Exception as e:
        error_msg = f"Data integration and import failed: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}


@shared_task
@task_utils.email_if_fails
def full_crawl_and_import_workflow():
    """
    Complete workflow: crawl all sources and import data

    This task orchestrates the entire crawling and import process:
    1. Crawl CourseSelection API data
    2. Crawl official website data
    3. Integrate and import all data

    Returns:
        dict: Results of complete workflow
    """
    workflow_results = {
        "coursesel_crawl": None,
        "official_crawl": None,
        "integration": None,
        "overall_status": "pending",
    }

    try:
        # Step 1: Crawl CourseSelection API
        print("Step 1: Crawling CourseSelection API...")
        workflow_results["coursesel_crawl"] = crawl_coursesel_data(jsessionid=None)

        # Step 2: Crawl official website
        print("Step 2: Crawling official website...")
        workflow_results["official_crawl"] = crawl_official_data()

        # Step 3: Integrate and import data
        print("Step 3: Integrating and importing data...")
        workflow_results["integration"] = integrate_and_import_data()

        # Determine overall status
        all_successful = all(
            result.get("status") == "success"
            for result in workflow_results.values()
            if result is not None
        )

        workflow_results["overall_status"] = (
            "success" if all_successful else "partial_success"
        )

        total_courses = workflow_results["integration"].get("imported_courses", 0)
        print(f"Workflow completed. Total courses imported: {total_courses}")

        return workflow_results

    except Exception as e:
        error_msg = f"Full crawl workflow failed: {str(e)}"
        print(error_msg)
        workflow_results["overall_status"] = "error"
        workflow_results["error_message"] = error_msg
        return workflow_results


# Legacy task functions - kept for compatibility but deprecated
# These should be removed in future versions

# @shared_task
# @task_utils.email_if_fails
# def crawl_orc():
#     """DEPRECATED: Use crawl_coursesel_data and crawl_official_data instead"""
#     print("WARNING: crawl_orc is deprecated. Use new crawler tasks instead.")
#     return full_crawl_and_import_workflow()

# @shared_task
# @task_utils.email_if_fails
# def crawl_program_url(url, program_code=None):
#     """DEPRECATED: Individual URL crawling no longer supported"""
#     print("WARNING: crawl_program_url is deprecated.")
#     return {"status": "deprecated", "message": "This function is no longer supported"}


# Commented out deprecated tasks for medians and timetable
# @shared_task
# @task_utils.email_if_fails
# def crawl_medians():
#     """DEPRECATED: Medians crawling for Dartmouth - not applicable to JI"""
#     pass

# @shared_task
# @task_utils.email_if_fails
# def crawl_timetable():
#     resource_name_fmt = "{term}_timetable"

#     # Crawl CURRENT_TERM
#     new_data = timetable.crawl_timetable(CURRENT_TERM)
#     CrawledData.objects.handle_new_crawled_data(
#         new_data,
#         resource_name_fmt.format(term=CURRENT_TERM.upper()),
#         CrawledData.COURSE_TIMETABLE,
#     )

# Crawl next term
# Since we are crawling the next term, we may get a couple course
# listings before the course offerings are actually posted, so we only
# act if there are more than 10 entries.
# next_term = get_next_term(CURRENT_TERM)
# new_data = timetable.crawl_timetable(next_term)
# if new_data and len(new_data) > 10:
#     CrawledData.objects.handle_new_crawled_data(
#         new_data,
#         resource_name_fmt.format(term=next_term.upper()),
#         CrawledData.COURSE_TIMETABLE,
#     )
