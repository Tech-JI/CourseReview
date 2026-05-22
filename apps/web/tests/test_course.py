import pytest
from django.urls import reverse

from apps.web.models import Review, Vote


@pytest.mark.django_db
class TestCourseAPIUnauthenticated:
    def test_list_courses_anonymous(self, base_client, course_factory):
        """Verify that any user can list courses with pagination."""
        # Create 3 courses using the factory
        course_factory.create_batch(3)

        url = reverse("courses_api")
        response = base_client.get(url)

        assert response.status_code == 200
        assert response.data["count"] == 3
        assert "results" in response.data

    def test_filter_courses_by_department(self, base_client, course_factory):
        """Verify filtering courses by department code."""
        # Create specific courses
        course_factory(department="MATH", course_code="MATH101J")
        course_factory(department="PHYS", course_code="PHYS101J")

        url = reverse("courses_api")
        # Test filtering for MATH department
        response = base_client.get(url, {"department": "MATH"})

        assert response.status_code == 200
        # Check that filtering worked (only 1 course returned)
        assert response.data["count"] == 1

        # Check course_code instead of department key
        # Since 'department' is not in the response, we verify 'MATH101J'
        assert response.data["results"][0]["course_code"] == "MATH101J"

    def test_filter_courses_by_code(self, base_client, course_factory):
        course_factory(course_code="PHYS101J")
        course_factory(course_code="MATH102J")
        course_factory(course_code="MATH101J")

        url = reverse("courses_api")

        response = base_client.get(url, {"code": "MATH"})
        assert response.status_code == 200
        assert response.data["count"] == 2

        response = base_client.get(url, {"code": "101"})
        assert response.data["count"] == 2

    def test_sort_courses_by_review_count_anonymous(
        self, base_client, user, course_factory
    ):
        c1 = course_factory(course_code="MATH101J")
        c2 = course_factory(course_code="MATH102J")
        Review.objects.create(
            course=c1, user=user, term="23S", professor="Prof X", comments="Great!"
        )

        url = reverse("courses_api")

        response = base_client.get(
            url, {"sort_by": "review_count", "sort_order": "desc"}
        )
        assert response.status_code == 200
        assert response.data["results"][0]["course_code"] == c1.course_code
        assert response.data["results"][1]["course_code"] == c2.course_code

    def test_sort_courses_by_score_anonymous(self, base_client, user, course_factory):
        c1 = course_factory(course_code="MATH101J")
        Vote.objects.create(
            user=user, course=c1, value=5, category=Vote.CATEGORIES.QUALITY
        )

        c2 = course_factory(course_code="MATH102J")
        Vote.objects.create(
            user=user, course=c2, value=1, category=Vote.CATEGORIES.QUALITY
        )

        url = reverse("courses_api")

        response = base_client.get(
            url, {"sort_by": "quality_score", "sort_order": "desc"}
        )
        assert response.status_code == 200
        assert response.data["results"][0]["course_code"] == "MATH102J"
        assert response.data["results"][1]["course_code"] == "MATH101J"

    def test_filter_courses_by_score_anonymous(self, base_client, user, course_factory):
        c1 = course_factory(course_code="MATH101J")
        Vote.objects.create(
            user=user, course=c1, value=5, category=Vote.CATEGORIES.QUALITY
        )

        c2 = course_factory(course_code="MATH102J")
        Vote.objects.create(
            user=user, course=c2, value=1, category=Vote.CATEGORIES.QUALITY
        )

        url = reverse("courses_api")

        response = base_client.get(url, {"min_quality": 4})
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_filter_courses_by_difficulty_anonymous(
        self, base_client, user, course_factory
    ):
        c1 = course_factory(course_code="MATH101J")
        Vote.objects.create(
            user=user, course=c1, value=5, category=Vote.CATEGORIES.DIFFICULTY
        )

        c2 = course_factory(course_code="MATH102J")
        Vote.objects.create(
            user=user, course=c2, value=1, category=Vote.CATEGORIES.DIFFICULTY
        )

        url = reverse("courses_api")

        response = base_client.get(url, {"min_difficulty": 4})
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_course_detail_retrieval(self, base_client, course):
        """Verify retrieving details for a specific course using its ID."""
        url = reverse("course_detail_api", kwargs={"course_id": course.id})
        response = base_client.get(url)

        assert response.status_code == 200
        # Verify the title matches the fixture-created course
        assert response.data["course_title"] == course.course_title

    def test_course_detail_fields_unauthenticated(self, base_client, course):
        url = reverse("course_detail_api", kwargs={"course_id": course.id})
        response = base_client.get(url)
        assert response.status_code == 200

        hidden_fields = [
            "quality_score",
            "difficulty_score",
            "difficulty_vote",
            "quality_vote",
            "quality_vote_count",
            "difficulty_vote_count",
        ]
        for field in hidden_fields:
            assert field not in response.data

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

    def test_department_api_empty(self, base_client, db):
        url = reverse("departments_api")
        response = base_client.get(url)
        assert response.status_code == 200
        assert response.data == []

    def test_department_api_sorting(self, base_client, course_factory):
        course_factory(department="ENGL", course_code="ENGL1000J")
        course_factory(department="MATH", course_code="MATH1560J")
        response = base_client.get(reverse("departments_api"))
        assert response.data[0]["code"] == "ENGL"


@pytest.mark.django_db
class TestCourseAPIAuthenticated:
    def test_sort_by_review_count(self, auth_client, user, course_factory):
        c_hot = course_factory(course_code="ENGR101J")
        course_factory(course_code="ENGR100J")
        Review.objects.create(
            course=c_hot, user=user, term="23S", professor="Prof X", comments="Great!"
        )
        url = reverse("courses_api")

        response = auth_client.get(
            url, {"sort_by": "review_count", "sort_order": "desc"}
        )

        results = response.data["results"]
        assert results[0]["course_code"] == "ENGR101J"
        assert results[1]["course_code"] == "ENGR100J"

    def test_filter_courses_by_quality(self, auth_client, user, course_factory):
        c1 = course_factory(course_code="MATH101J")
        Vote.objects.create(
            user=user, course=c1, value=5, category=Vote.CATEGORIES.QUALITY
        )

        c2 = course_factory(course_code="MATH102J")
        Vote.objects.create(
            user=user, course=c2, value=1, category=Vote.CATEGORIES.QUALITY
        )

        url = reverse("courses_api")

        response = auth_client.get(url, {"min_quality": 4})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["course_code"] == "MATH101J"

    def test_filter_courses_by_difficulty(self, auth_client, user, course_factory):
        c1 = course_factory(course_code="MATH101J")
        Vote.objects.create(
            user=user, course=c1, value=5, category=Vote.CATEGORIES.DIFFICULTY
        )

        c2 = course_factory(course_code="MATH102J")
        Vote.objects.create(
            user=user, course=c2, value=1, category=Vote.CATEGORIES.DIFFICULTY
        )

        url = reverse("courses_api")

        response = auth_client.get(url, {"min_difficulty": 4})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["course_code"] == "MATH101J"

    def test_sort_courses_by_quality_score(self, auth_client, user, course_factory):
        c1 = course_factory(course_code="MATH101J")
        Vote.objects.create(
            user=user, course=c1, value=5, category=Vote.CATEGORIES.QUALITY
        )

        c2 = course_factory(course_code="MATH102J")
        Vote.objects.create(
            user=user, course=c2, value=1, category=Vote.CATEGORIES.QUALITY
        )

        url = reverse("courses_api")

        response = auth_client.get(
            url, {"sort_by": "quality_score", "sort_order": "desc"}
        )
        assert response.status_code == 200
        assert response.data["results"][0]["course_code"] == "MATH101J"

    def test_sort_courses_by_difficulty_score(self, auth_client, user, course_factory):
        c1 = course_factory(course_code="MATH101J")
        Vote.objects.create(
            user=user, course=c1, value=5, category=Vote.CATEGORIES.DIFFICULTY
        )

        c2 = course_factory(course_code="MATH102J")
        Vote.objects.create(
            user=user, course=c2, value=1, category=Vote.CATEGORIES.DIFFICULTY
        )

        url = reverse("courses_api")

        response = auth_client.get(
            url, {"sort_by": "difficulty_score", "sort_order": "desc"}
        )
        assert response.status_code == 200
        assert response.data["results"][0]["course_code"] == "MATH101J"

    def test_sort_order_asc_and_desc(self, auth_client, course_factory):
        course_factory(course_code="MATH101J")
        course_factory(course_code="PHY101J")

        url = reverse("courses_api")

        # case 1: Ascending
        res_asc = auth_client.get(url, {"sort_by": "course_code", "sort_order": "asc"})
        assert res_asc.data["results"][0]["course_code"] == "MATH101J"
        assert res_asc.data["results"][1]["course_code"] == "PHY101J"

        # case 2: Descending
        res_desc = auth_client.get(
            url, {"sort_by": "course_code", "sort_order": "desc"}
        )
        assert res_desc.data["results"][0]["course_code"] == "PHY101J"
        assert res_desc.data["results"][1]["course_code"] == "MATH101J"

    def test_course_detail_fields_authenticated(self, auth_client, course):
        url = reverse("course_detail_api", kwargs={"course_id": course.id})
        response = auth_client.get(url)
        assert response.status_code == 200

        required_fields = [
            "quality_score",
            "difficulty_score",
            "difficulty_vote",
            "quality_vote",
            "quality_vote_count",
            "difficulty_vote_count",
        ]
        for field in required_fields:
            assert field in response.data
