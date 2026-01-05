import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestCourseManagement:
    def test_list_courses_pagination(self, base_client, course_factory):
        course_factory.create_batch(3)
        url = reverse("courses_api")
        response = base_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 3

    def test_course_detail_retrieval(self, base_client, course):
        url = reverse("course_detail_api", kwargs={"course_id": course.id})
        response = base_client.get(url)
        assert response.status_code == 200
        assert response.data["course_title"] == course.course_title
