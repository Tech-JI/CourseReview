import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from apps.web.tests import factories

# -------------------------------------------------------------------------
# 1. Clients & Authentication
# -------------------------------------------------------------------------


@pytest.fixture
def base_client():
    """Returns an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Returns a saved user instance."""
    return factories.UserFactory()


@pytest.fixture
def auth_client(user, base_client):
    """Returns an API client authenticated as the 'user' fixture."""
    base_client.force_authenticate(user=user)
    return base_client


# -------------------------------------------------------------------------
# 2. Data Fixtures (Models)
# -------------------------------------------------------------------------


@pytest.fixture
def course(db):
    """Returns a saved course instance."""
    return factories.CourseFactory()


@pytest.fixture
def course_batch(db):
    """Returns a batch of 3 general courses."""
    return factories.CourseFactory.create_batch(3)


@pytest.fixture
def department_mixed_courses(db):
    """Returns a mixed set of courses for filtering/sorting tests."""
    # Note: Using course_title to match current course model field
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
    """Returns a saved review instance belonging to 'user'."""
    return factories.ReviewFactory(course=course, user=user, comments="a" * min_len)


@pytest.fixture
def other_review(db):
    """Returns a review belonging to a different user for security testing."""
    from apps.web.tests.factories import UserFactory, ReviewFactory

    return ReviewFactory(user=UserFactory())


@pytest.fixture
def course_factory(db):
    """Access the factory class directly for custom batch creation."""
    return factories.CourseFactory


# -------------------------------------------------------------------------
# 3. Validation & Payloads
# -------------------------------------------------------------------------


@pytest.fixture
def min_len():
    """Retrieves the minimum comment length from project settings."""
    return settings.WEB["REVIEW"]["COMMENT_MIN_LENGTH"]


@pytest.fixture
def valid_review_data(min_len):
    """Generates a valid payload for review creation/update tests."""
    return {
        "term": "23F",
        "professor": "Dr. Testing",
        "comments": "a" * min_len,
    }


# -------------------------------------------------------------------------
# 4. URL Fixtures (Routing)
# -------------------------------------------------------------------------


@pytest.fixture
def course_reviews_url(course):
    """URL for listing/posting reviews for a specific course."""
    return reverse("course_review_api", kwargs={"course_id": course.id})


@pytest.fixture
def personal_reviews_list_url():
    """URL for the current user's personal review list."""
    return reverse("user_reviews_api")


@pytest.fixture
def personal_review_detail_url(review):
    """URL for GET/PUT/DELETE a specific review owned by the user."""
    return reverse("user_review_api", kwargs={"review_id": review.id})


@pytest.fixture
def other_review_detail_url(other_review):
    """URL for a review NOT owned by the current user (used for 404/Security)."""
    return reverse("user_review_api", kwargs={"review_id": other_review.id})
