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

    def test_course_vote_difficulty(self, auth_client, course):
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        data = {"value": 5, "forLayup": True}
        response = auth_client.post(url, data, content_type="application/json")
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["new_score"] is not None

    def test_course_vote_change(self, auth_client, course):
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        auth_client.post(
            url, {"value": 1, "forLayup": False}, content_type="application/json"
        )
        data = {"value": 5, "forLayup": False}
        response = auth_client.post(url, data, content_type="application/json")
        assert response.status_code == 200
        res_json = response.json()
        if "new_score" in res_json:
            assert res_json["new_score"] == 5.0

    def test_course_vote_cancel(self, auth_client, course):
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        data = {"value": 5, "forLayup": False}
        resp1 = auth_client.post(url, data, content_type="application/json")
        assert resp1.status_code == 200
        assert resp1.json()["was_unvote"] is False
        resp2 = auth_client.post(url, data, content_type="application/json")
        assert resp2.status_code == 200
        res_json = resp2.json()
        assert res_json["was_unvote"] is True
        if "new_vote_count" in res_json:
            assert res_json["new_vote_count"] == 0

    # verifying that unauthenticated users cannot vote on a course.
    def test_course_vote_unauthenticated(self, base_client, course):
        url = reverse("course_vote_api", kwargs={"course_id": course.id})
        data = {"value": 5, "forLayup": False}
        response = base_client.post(url, data, content_type="application/json")
        assert response.status_code in [401, 403]

    # verifying that unauthenticated users cannot upvote a review.
    def test_review_vote_unauthenticated(self, base_client, review):
        url = reverse("review_vote_api", kwargs={"review_id": review.id})
        data = {"is_kudos": True}
        response = base_client.post(url, data, content_type="application/json")
        assert response.status_code in [401, 403]
