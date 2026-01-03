import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAuthentication:
    """Tests for user authentication and status endpoints"""

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
