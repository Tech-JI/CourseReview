import csv
from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.web.management.commands.import_legacy_reviews import IMPORT_USERNAME
from apps.web.models import Course, Review


def review_csv(
    *, course_code="TEST1000J", professor="Professor", term="", comment="Comment"
):
    content = StringIO()
    writer = csv.DictWriter(
        content, fieldnames=["course_code", "professor", "term", "comment"]
    )
    writer.writeheader()
    writer.writerow(
        {
            "course_code": course_code,
            "professor": professor,
            "term": term,
            "comment": comment,
        }
    )
    return SimpleUploadedFile(
        "legacy_reviews.csv",
        content.getvalue().encode("utf-8"),
        content_type="text/csv",
    )


@pytest.fixture
def superuser():
    return User.objects.create_superuser("admin", "admin@example.com", "password123")


@pytest.fixture
def import_url():
    return reverse("admin:web_review_import_legacy_reviews")


@pytest.mark.django_db
def test_only_superusers_can_access_legacy_review_import(client, import_url):
    staff_user = User.objects.create_user(
        "staff", "staff@example.com", "password123", is_staff=True
    )
    client.force_login(staff_user)

    response = client.get(import_url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_preview_then_confirm_imports_uploaded_csv(client, superuser, import_url):
    Course.objects.create(course_code="TEST1000J")
    client.force_login(superuser)

    preview = client.post(
        import_url,
        {
            "action": "preview",
            "expected_count": 1,
            "csv_file": review_csv(),
        },
    )

    assert preview.status_code == 200
    assert b"DRY-RUN only; no data was written." in preview.content
    assert b"Confirm and import reviews" in preview.content
    assert Review.objects.count() == 0
    assert IMPORT_USERNAME not in User.objects.values_list("username", flat=True)

    imported = client.post(import_url, {"action": "execute"})

    assert imported.status_code == 200
    assert b"Inserted reviews: 1" in imported.content
    assert Review.objects.count() == 1
    assert Review.objects.get().course.course_code == "TEST1000J"


@pytest.mark.django_db
def test_admin_cannot_execute_without_a_dry_run(client, superuser, import_url):
    Course.objects.create(course_code="TEST1000J")
    client.force_login(superuser)

    response = client.post(import_url, {"action": "execute"})

    assert response.status_code == 200
    assert b"Run a dry-run with a CSV before importing." in response.content
    assert Review.objects.count() == 0
