"""Professor-name canonicalization on review submission.

New reviews must attribute the professor using the course's canonical
Instructor names (from course offerings): reversed / misspelled / annotated
variants are corrected automatically; only names that match nothing are kept
as their own professor.
"""

import pytest
from rest_framework import status

from apps.web.models import Review
from apps.web.tests import factories
from lib.name_normalization import canonicalize_professor

# ---------------------------------------------------------------------------
# Pure lib tests
# ---------------------------------------------------------------------------


def test_canonicalize_matches_reversed_and_misspelled():
    assert canonicalize_professor("Lin Zibo", ["Zibo Lin"]) == "Zibo Lin"
    assert canonicalize_professor("lin zibo", ["Zibo Lin"]) == "Zibo Lin"
    assert (
        canonicalize_professor("Manuel Charlamagne", ["Manuel Charlemagne"])
        == "Manuel Charlemagne"
    )
    assert (
        canonicalize_professor("Aline Chevelier", ["Aline Chevalier"])
        == "Aline Chevalier"
    )
    assert canonicalize_professor("Kwee-yan Teh", ["Kwee-Yan Teh"]) == "Kwee-Yan Teh"
    assert canonicalize_professor("Horst Hohberger", ["Horst Harold Hohberger"]) == (
        "Horst Harold Hohberger"
    )
    assert (
        canonicalize_professor("Nick Welchbolen", ["Nicholas Scott Welch-Bolen"])
        == "Nicholas Scott Welch-Bolen"
    )


def test_canonicalize_unmatched_names_are_kept():
    assert canonicalize_professor("John Smith", ["Zibo Lin"]) == "John Smith"
    assert canonicalize_professor("olga danilkina", []) == "Olga Danilkina"
    # Title + single name is not a valid new name; preserved verbatim.
    assert canonicalize_professor("Dr. Testing", []) == "Dr. Testing"
    assert canonicalize_professor("", ["Zibo Lin"]) == ""


def test_canonicalize_does_not_force_unverifiable_typos():
    # Jayhang/Jaehyung is a 4-edit drift; without other evidence it must stay.
    assert canonicalize_professor("Jayhang Ju", ["Jaehyung Ju"]) == "Jayhang Ju"


# ---------------------------------------------------------------------------
# API tests: professor corrected to the course's instructor name
# ---------------------------------------------------------------------------


@pytest.fixture
def course_with_instructor(course):
    offering = factories.CourseOfferingFactory(course=course, term="26SU")
    offering.instructors.add(factories.InstructorFactory(name="Zibo Lin"))
    return course, offering.instructors.get()


@pytest.mark.django_db
def test_create_review_corrects_reversed_professor(
    auth_client, course_reviews_url, min_len, course_with_instructor
):
    course, _ = course_with_instructor
    response = auth_client.post(
        course_reviews_url,
        {
            "term": "26SU",
            "professor": "Lin Zibo",
            "comments": "c" * min_len,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Review.objects.get(course=course).professor == "Zibo Lin"


@pytest.mark.django_db
def test_create_review_corrects_misspelled_professor(
    auth_client, course_reviews_url, course, min_len
):
    offering = factories.CourseOfferingFactory(course=course, term="26SU")
    offering.instructors.add(factories.InstructorFactory(name="Manuel Charlemagne"))
    response = auth_client.post(
        course_reviews_url,
        {
            "term": "26SU",
            "professor": "Manuel Charlamagne",
            "comments": "c" * min_len,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Review.objects.get(course=course).professor == "Manuel Charlemagne"


@pytest.mark.django_db
def test_create_review_keeps_unmatched_professor(
    auth_client, course_reviews_url, course, min_len
):
    offering = factories.CourseOfferingFactory(course=course, term="26SU")
    offering.instructors.add(factories.InstructorFactory(name="Zibo Lin"))
    response = auth_client.post(
        course_reviews_url,
        {
            "term": "26SU",
            "professor": "John Smith",
            "comments": "c" * min_len,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Review.objects.get(course=course).professor == "John Smith"


@pytest.mark.django_db
def test_update_review_corrects_professor_via_instance_course(
    auth_client, course, user, min_len
):
    """PUT has no course in context; it must fall back to the review's course."""
    from django.urls import reverse

    offering = factories.CourseOfferingFactory(course=course, term="26SU")
    offering.instructors.add(factories.InstructorFactory(name="Zibo Lin"))
    review = factories.ReviewFactory(
        course=course, user=user, professor="Zibo Lin", comments="c" * min_len
    )
    url = reverse("user_review_api", kwargs={"review_id": review.id})
    response = auth_client.put(
        url,
        {"term": "26SU", "professor": "Lin Zibo", "comments": "c" * min_len},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    review.refresh_from_db()
    assert review.professor == "Zibo Lin"


@pytest.mark.django_db
def test_single_word_professor_still_rejected(
    auth_client, course_reviews_url, course, min_len
):
    offering = factories.CourseOfferingFactory(course=course, term="26SU")
    offering.instructors.add(factories.InstructorFactory(name="Zibo Lin"))
    response = auth_client.post(
        course_reviews_url,
        {"term": "26SU", "professor": "Zibo", "comments": "c" * min_len},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
