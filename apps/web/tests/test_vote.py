import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestVotingSystem:
    """
    Tests for the voting system:
    - Course quality/difficulty votes
    - Review kudos/dislike votes
    - Vote validation (valid ranges)
    """

    def test_course_vote_quality(self, auth_client, course):
        """Test voting for course quality (forLayup=False)."""
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        data = {"value": 5, "forLayup": False}
        response = auth_client.post(url, data, format="json")

        assert response.status_code == 200
        assert response.data["new_vote_count"] == 1
        assert response.data["new_score"] == 5.0

    def test_course_vote_invalid_range(self, auth_client, course):
        """Test that voting with a value outside 1-5 is rejected."""
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        data = {"value": 10, "forLayup": False}
        response = auth_client.post(url, data, format="json")

        # Should be 400 according to standard API validation rules
        assert response.status_code == 400

    def test_review_vote_kudos(self, auth_client, review):
        """Test giving a kudos (upvote) to a review."""
        url = reverse("review_vote_api", kwargs={"review_id": review.id})
        data = {"is_kudos": True}
        response = auth_client.post(url, data, format="json")

        assert response.status_code == 200
        assert response.data["kudos_count"] == 1
        assert response.data["user_vote"] is True
