import pytest
from django.urls import reverse
from apps.web.models import Review


@pytest.mark.django_db
class TestReviewManagement:
    """
    Tests for Review management:
    - Creation with validation (30+ chars, valid term)
    - Retrieval and filtering (q search, author=me)
    - Updates and deletions with permissions
    """

    def test_create_review_success(self, auth_client, course):
        """Test successful review creation by an authenticated user."""
        url = reverse("course_review_api", kwargs={"course_id": course.id})
        data = {
            "term": "24S",
            "professor": "Dr. Zhang",
            "comments": "This course provided a deep understanding of the subject matter and the projects were quite challenging but rewarding.",
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 201
        assert Review.objects.filter(course=course).count() == 1

    def test_create_review_validation_error(self, auth_client, course):
        """Test validation: too short comments (under 30 chars) and invalid term format."""
        url = reverse("course_review_api", kwargs={"course_id": course.id})

        # Scenario 1: Comments too short
        data = {"term": "24S", "comments": "Way too short."}
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 400
        assert "comments" in response.data

    def test_get_reviews_filtering(self, auth_client, user, course, review):
        """Test filtering reviews using 'q' (search) and 'author=me' parameters."""
        url = reverse("course_review_api", kwargs={"course_id": course.id})

        # Test author=me (the 'review' fixture belongs to 'user' by default)
        response = auth_client.get(url, {"author": "me"})
        assert response.status_code == 200
        assert len(response.data) == 1

        # Test keyword search
        response = auth_client.get(url, {"q": review.comments[:10]})
        assert len(response.data) >= 1

    def test_update_own_review(self, auth_client, course, review):
        """Test that a user can update their own review."""
        url = reverse("user_review_api", kwargs={"review_id": review.id})
        updated_data = {
            "course": course.id,
            "term": "24F",
            "professor": "New Prof",
            "comments": "Updated review content that is still over thirty characters long for validation.",
        }
        response = auth_client.put(url, updated_data, format="json")
        assert response.status_code == 200
        review.refresh_from_db()
        assert review.professor == "New Prof"

    def test_delete_own_review(self, auth_client, review):
        """Test that a user can delete their own review."""
        url = reverse("user_review_api", kwargs={"review_id": review.id})
        response = auth_client.delete(url)
        assert response.status_code == 204
        assert Review.objects.filter(id=review.id).count() == 0
