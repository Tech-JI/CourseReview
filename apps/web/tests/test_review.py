import pytest
from django.urls import reverse
from rest_framework import status

from apps.web.models import Review
from apps.web.tests.factories import ReviewFactory


@pytest.mark.django_db
class TestReviewAPIUnauthenticated:
    def test_get_course_reviews_anonymous(self, base_client, course_reviews_url):
        """1. Verify anonymous users cannot list course reviews."""
        response = base_client.get(course_reviews_url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_get_personal_reviews_anonymous(
        self, base_client, personal_reviews_list_url
    ):
        """2. Verify anonymous users cannot access personal review list."""
        response = base_client.get(personal_reviews_list_url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_delete_review_anonymous_forbidden(self, base_client, review):
        """3. Verify that unauthenticated users are forbidden from deleting reviews."""
        url = reverse("user_review_api", kwargs={"review_id": review.id})
        response = base_client.delete(url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
        assert Review.objects.filter(id=review.id).exists()

    def test_review_detail_anonymous_forbidden(
        self, base_client, personal_review_detail_url
    ):
        response = base_client.get(personal_review_detail_url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]


@pytest.mark.django_db
class TestReviewAPIAuthenticated:
    def test_create_review_success(
        self, auth_client, course_reviews_url, course, valid_review_data
    ):
        """4. Verify successful review creation with valid data."""
        response = auth_client.post(
            course_reviews_url, valid_review_data, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Review.objects.filter(course=course).count() == 1

    def test_list_personal_reviews(
        self, auth_client, personal_reviews_list_url, review, other_review
    ):
        """5. Verify user can list their own reviews."""
        response = auth_client.get(personal_reviews_list_url)
        assert response.status_code == status.HTTP_200_OK
        assert any(r["id"] == review.id for r in response.data)
        assert all(r["id"] != other_review.id for r in response.data)

    def test_retrieve_review_detail(
        self, auth_client, personal_review_detail_url, review
    ):
        """6. Verify user can retrieve their own review details."""
        response = auth_client.get(personal_review_detail_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == review.id

    def test_filter_reviews_by_author_me(self, auth_client, course_reviews_url, review):
        """7. Verify 'author=me' filters reviews for a specific course."""
        ReviewFactory(course=review.course)
        response = auth_client.get(course_reviews_url, {"author": "me"})
        assert response.status_code == status.HTTP_200_OK
        assert [r["id"] for r in response.data] == [review.id]

    def test_search_reviews_by_professor(
        self, auth_client, course_reviews_url, course, min_len
    ):
        """8. Verify search 'q' works for professor names."""
        ReviewFactory(course=course, professor="UniqueProf", comments="c" * min_len)
        ReviewFactory(course=course, professor="OtherProf", comments="c" * min_len)
        response = auth_client.get(course_reviews_url, {"q": "UniqueProf"})
        assert all(r["professor"] == "UniqueProf" for r in response.data)

    def test_update_review_success(
        self, auth_client, personal_review_detail_url, review, valid_review_data
    ):
        """9. Verify successful update of user's own review."""
        valid_review_data["comments"] = "b" * len(valid_review_data["comments"])
        response = auth_client.put(
            personal_review_detail_url, valid_review_data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        review.refresh_from_db()
        assert review.comments == valid_review_data["comments"]

    def test_delete_review_success(
        self, auth_client, personal_review_detail_url, review
    ):
        """10. Verify successful deletion of user's own review."""
        response = auth_client.delete(personal_review_detail_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Review.objects.filter(id=review.id).exists()

    def test_create_validation_length_error(
        self, auth_client, course_reviews_url, valid_review_data, min_len
    ):
        """13. Verify rejection of comments shorter than min_length."""
        valid_review_data["comments"] = "a" * (min_len - 1)
        response = auth_client.post(
            course_reviews_url, valid_review_data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_validation_missing_field(
        self, auth_client, personal_review_detail_url, min_len
    ):
        """14. Verify PUT fails if required fields (professor) are missing."""
        response = auth_client.put(
            personal_review_detail_url,
            {"comments": "b" * min_len},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_review_denied(self, auth_client, review, valid_review_data):
        """15. Verify user cannot review the same course twice (403)."""
        url = reverse("course_review_api", kwargs={"course_id": review.course.id})
        response = auth_client.post(url, valid_review_data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_access_other_user_review_404(self, auth_client, other_review_detail_url):
        """16. Security: Verify user cannot access someone else's review ID."""
        response = auth_client.get(other_review_detail_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_to_invalid_course_id(self, auth_client, valid_review_data):
        """18. Verify posting to non-existent course ID returns 404."""
        url = reverse("course_review_api", kwargs={"course_id": 88888})
        response = auth_client.post(url, valid_review_data, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_review_response_contains_votes(
        self, auth_client, personal_review_detail_url
    ):
        """19. Verify vote statistics are included in the response."""
        response = auth_client.get(personal_review_detail_url)
        assert "kudos_count" in response.data
        assert "dislike_count" in response.data
