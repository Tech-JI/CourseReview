import pytest
from django.urls import reverse
from apps.web.models import Review


@pytest.mark.django_db
class TestReviewManagement:
    def test_create_review_success(self, auth_client, course):
        url = reverse("course_review_api", kwargs={"course_id": course.id})
        data = {
            "term": "23F",
            "professor": "Dr. Li",
            "comments": "This course was absolutely amazing and I learned a lot of practical skills that will be very useful for my future career.",
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 201
        assert Review.objects.filter(course=course).count() == 1

    def test_vote_on_review(self, auth_client, review):
        url = reverse("review_vote_api", kwargs={"review_id": review.id})
        response = auth_client.post(url, {"is_kudos": True}, format="json")
        assert response.status_code == 200
        assert response.data["kudos_count"] == 1
