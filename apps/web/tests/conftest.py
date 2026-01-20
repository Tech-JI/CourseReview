import pytest
from rest_framework.test import APIClient
from apps.web.tests import factories
from django.conf import settings
from django.urls import reverse


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
def course_batch(db):
    """3 general courses"""
    return factories.CourseFactory.create_batch(3)


@pytest.fixture
def department_mixed_courses(db):
    """set with specific section"""
    return [
        factories.CourseFactory(
            department="MATH",
            course_title="Honors Calculus II",
            course_code="MATH1560J",
        ),
        factories.CourseFactory(
            department="MATH", course_title="Calculus II", course_code="MATH1160J"
        ),
        factories.CourseFactory(
            department="CHEM", course_title="Chemistry", course_code="CHEM2100J"
        ),
    ]


@pytest.fixture
def review(db, course, user, min_len):
    """Fixture to provide a saved review instance with valid length."""
    return factories.ReviewFactory(course=course, user=user, comments="a" * min_len)


@pytest.fixture
def min_len():
    """Retrieves the minimum comment length from project settings."""
    return settings.WEB["REVIEW"]["COMMENT_MIN_LENGTH"]


@pytest.fixture
def valid_review_data(min_len):
    """Generates a valid payload for review creation tests."""
    return {
        "term": "23F",
        "professor": "Dr. Testing",
        "comments": "a" * min_len,  # Dynamically adjust to settings
    }


@pytest.fixture
def course_factory(db):
    """Fixture to access the factory class directly for batch creation"""
    return factories.CourseFactory


@pytest.fixture
def user_reviews_url():
    """URL for the list of current user's reviews."""
    return reverse("user_reviews_api")


@pytest.fixture
def own_review_url(review):
    """URL for a specific review owned by the current user."""
    return reverse("user_review_api", kwargs={"review_id": review.id})


@pytest.fixture
def other_review(db):
    """A review belonging to a different user."""
    from apps.web.tests.factories import ReviewFactory, UserFactory

    return ReviewFactory(user=UserFactory())


@pytest.fixture
def other_review_url(other_review):
    """URL for a review NOT owned by the current user."""
    return reverse("user_review_api", kwargs={"review_id": other_review.id})
