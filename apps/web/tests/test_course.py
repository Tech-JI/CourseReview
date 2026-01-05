import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestCourseManagement:
    """
    Tests for course-related endpoints:
    - Course listing and filtering
    - Course details retrieval
    - Department listings
    """

    def test_list_courses_anonymous(self, base_client, course_factory):
        """Verify that any user can list courses with pagination."""
        # Create 3 courses using the factory
        course_factory.create_batch(3)

        url = reverse("courses_api")
        response = base_client.get(url)

        assert response.status_code == 200
        assert response.data["count"] >= 3
        assert "results" in response.data

    def test_filter_courses_by_department(self, base_client, course_factory):
        """Verify filtering courses by department code."""
        # Create specific courses
        course_factory(department="MATH", course_code="MATH101")
        course_factory(department="PHYS", course_code="PHYS101")

        url = reverse("courses_api")
        # Test filtering for MATH department
        response = base_client.get(url, {"department": "MATH"})

        assert response.status_code == 200
        # Check that filtering worked (only 1 course returned)
        assert response.data["count"] == 1

        # FIX: Check course_code instead of department key
        # Since 'department' is not in the response, we verify 'MATH101'
        assert response.data["results"][0]["course_code"] == "MATH101"

    def test_course_detail_retrieval(self, base_client, course):
        """Verify retrieving details for a specific course using its ID."""
        url = reverse("course_detail_api", kwargs={"course_id": course.id})
        response = base_client.get(url)

        assert response.status_code == 200
        # Verify the title matches the fixture-created course
        assert response.data["course_title"] == course.course_title

    def test_department_listings(self, base_client, course_factory):
        """Verify the endpoint that lists all departments and their course counts."""
        course_factory(department="MATH")
        course_factory(department="MATH")
        course_factory(department="EECS")

        url = reverse("departments_api")
        response = base_client.get(url)

        assert response.status_code == 200
        assert isinstance(response.data, list)

        # Find MATH department in the list
        math_dept = next(item for item in response.data if item["code"] == "MATH")
        assert math_dept["count"] == 2
