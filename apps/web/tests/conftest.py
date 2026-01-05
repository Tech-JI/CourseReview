import pytest
from rest_framework.test import APIClient
from apps.web.tests import factories


# 1. Anonymous Client (Base Client)
@pytest.fixture
def base_client():
    """Returns an unauthenticated API client."""
    return APIClient()


# 2. User Fixture
@pytest.fixture
def user(db):
    """Returns a saved user instance."""
    return factories.UserFactory()


# 3. Authenticated Client
@pytest.fixture
def auth_client(user, base_client):
    """Returns an API client authenticated as the 'user' fixture."""
    base_client.force_authenticate(user=user)
    return base_client


# 4. Data Fixtures (Wrapped Factories)
@pytest.fixture
def course(db):
    """Returns a saved course instance."""
    return factories.CourseFactory()


@pytest.fixture
def review(db, course, user):
    """Returns a saved review instance."""
    return factories.ReviewFactory(course=course, user=user)


@pytest.fixture
def course_factory(db):
    """Fixture to access the factory class directly for batch creation"""
