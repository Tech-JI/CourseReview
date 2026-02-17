import pytest
from django.urls import reverse

from apps.web.tests.factories import ReviewFactory


@pytest.mark.django_db
class TestUserStatusAPI:
    def test_user_status_anonymous(self, base_client):
        """Test that unauthenticated users get isAuthenticated=False"""
        url = reverse("user_status")
        response = base_client.get(url)

        assert response.status_code == 200
        assert response.data["isAuthenticated"] is False
        assert "username" not in response.data

    def test_user_status_authenticated(self, auth_client, user):
        """Test that authenticated users get isAuthenticated=True and their username"""
        url = reverse("user_status")
        # auth_client is already logged in via the fixture in conftest.py
        response = auth_client.get(url)

        assert response.status_code == 200
        assert response.data["isAuthenticated"] is True
        assert response.data["username"] == user.username


@pytest.mark.django_db
class TestLandingPageAPI:
    def test_landing_page_review_count(self, base_client, review):
        """Verify landing page shows correct review statistics."""
        url = reverse("landing_api")
        response = base_client.get(url)
        assert response.status_code == 200
        # Should be at least 1 due to the 'review' fixture
        assert response.data["review_count"] == 1

    def test_landing_page_review_count_empty(self, base_client, db):
        """Verify review count is 0 when no reviews exist in the database."""
        url = reverse("landing_api")
        response = base_client.get(url)

        assert response.status_code == 200
        assert response.data["review_count"] == 0

    def test_landing_page_review_count_multiple(self, base_client, db):
        """Verify review count returns the correct total when multiple reviews exist."""
        # Create 5 reviews across different courses/users
        ReviewFactory.create_batch(5)

        url = reverse("landing_api")
        response = base_client.get(url)

        assert response.status_code == 200
        assert response.data["review_count"] == 5
