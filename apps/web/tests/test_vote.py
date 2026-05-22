import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestCourseVoteAPIAuthenticated:
    def test_course_vote_quality_success(self, auth_client, course):
        """Test authenticated user voting for course quality."""
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        data = {"value": 5, "forLayup": False}
        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "new_score" in response.data
        assert response.data["new_vote_count"] == 1
        assert response.data["was_unvote"] is False

    def test_course_vote_change_value(self, auth_client, course):
        """Verify user can change their vote value (e.g., from 5 to 3)."""
        url = reverse("course_vote_api", kwargs={"course_id": course.id})

        # Initial vote
        auth_client.post(url, {"value": 5, "forLayup": False}, format="json")
        # Change vote
        response = auth_client.post(url, {"value": 3, "forLayup": False}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["new_score"] == 3.0
        assert response.data["new_vote_count"] == 1  # Count stays same

    def test_course_vote_cancel(self, auth_client, course):
        """Verify voting the same value twice cancels (unvotes) the vote."""
        url = reverse("course_vote_api", kwargs={"course_id": course.id})

        auth_client.post(url, {"value": 5, "forLayup": False}, format="json")
        # Vote same value again to toggle off
        response = auth_client.post(url, {"value": 5, "forLayup": False}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["was_unvote"] is True
        assert response.data["new_vote_count"] == 0

    def test_course_vote_invalid_range_400(self, auth_client, course):
        """Verify 400 error for scores outside 1-5."""
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        response = auth_client.post(
            url, {"value": 10, "forLayup": False}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCourseVoteAPIUnauthenticated:
    def test_course_vote_anonymous_denied(self, base_client, course):
        """Verify unauthenticated users cannot vote."""
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        response = base_client.post(url, {"value": 5, "forLayup": False}, format="json")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]


@pytest.mark.django_db
class TestReviewVoteAPIAuthenticated:
    def test_review_vote_kudos_success(self, auth_client, review):
        """Test authenticated user giving kudos to a review."""
        url = reverse("review_vote_api", kwargs={"review_id": review.id})
        data = {"is_kudos": True}
        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["kudos_count"] == 1
        assert response.data["user_vote"] is True

    def test_review_vote_toggle_off(self, auth_client, review):
        """Verify that clicking kudos twice cancels the vote."""
        url = reverse("review_vote_api", kwargs={"review_id": review.id})

        auth_client.post(url, {"is_kudos": True}, format="json")
        # Second click
        response = auth_client.post(url, {"is_kudos": True}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["kudos_count"] == 0
        assert response.data["user_vote"] is None

    def test_review_vote_not_found_404(self, auth_client):
        """Verify 404 for non-existent review ID."""
        url = reverse("review_vote_api", kwargs={"review_id": 99999})
        response = auth_client.post(url, {"is_kudos": True}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestReviewVoteAPIUnauthenticated:
    def test_review_vote_anonymous_denied(self, base_client, review):
        """Verify unauthenticated users cannot vote on reviews."""
        url = reverse("review_vote_api", kwargs={"review_id": review.id})
        response = base_client.post(url, {"is_kudos": True}, format="json")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
