import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from apps.web.models import Syllabus, SyllabusFile
from apps.web.tests.factories import (
    CourseOfferingFactory,
    InstructorFactory,
    SyllabusFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _scratch_media(eager_media):
    """Every test here runs against a scratch MEDIA_ROOT with eager Celery."""
    return eager_media


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _offering_with_instructor(course, instructor=None):
    offering = CourseOfferingFactory(course=course)
    instructor = instructor or InstructorFactory()
    offering.instructors.add(instructor)
    return instructor


def _make_pdf_upload(content=b"%PDF fake syllabus", name="syllabus.pdf"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


@pytest.fixture
def syllabus_urls(course):
    return {
        "list": reverse("course_syllabi_api", kwargs={"course_id": course.id}),
        "detail": lambda sid: reverse(
            "syllabus_detail_api", kwargs={"syllabus_id": sid}
        ),
        "download": lambda sid: reverse(
            "syllabus_download_api", kwargs={"syllabus_id": sid}
        ),
    }


@pytest.fixture
def fake_ollama(monkeypatch):
    """Runs analysis inline with a canned verdict; comparison switches on prompt."""

    def _chat(messages, format_json=False):
        prompt = messages[0]["content"]
        if isinstance(prompt, list):
            prompt = "\n".join(p.get("text", "") for p in prompt)
        if "Two syllabus versions exist" in prompt:
            result = {
                "newer": True,
                "better_match": True,
                "more_authentic": True,
                "recommendation": "keep_new",
                "notes": "mock",
            }
        else:
            result = {
                "match_score": 88,
                "matches_course_content": True,
                "is_legitimate": True,
                "flags": [],
                "summary_md": "## Summary\n\nMock grading summary.",
            }
        return {"content": json.dumps(result)}

    monkeypatch.setattr("apps.web.syllabus_analysis.ollama_chat", _chat)
    return _chat


@pytest.fixture
def fake_extraction(monkeypatch):
    """Skips real PDF parsing in the eager task."""

    def _extract(file_obj):
        return "This course covers calculus and linear algebra topics."

    monkeypatch.setattr("apps.web.tasks._extract_or_ocr", _extract)


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------


class TestUpload:
    def test_upload_requires_auth(self, base_client, syllabus_urls):
        response = base_client.post(syllabus_urls["list"], {}, format="multipart")
        assert response.status_code in (401, 403)

    def test_unknown_course_404(self, auth_client, course, db):
        url = reverse("course_syllabi_api", kwargs={"course_id": 999999})
        response = auth_client.post(url, {}, format="multipart")
        assert response.status_code == 404

    def test_rejects_unsupported_extension(self, auth_client, course, syllabus_urls):
        instructor = _offering_with_instructor(course)
        upload = _make_pdf_upload(name="syllabus.exe")
        response = auth_client.post(
            syllabus_urls["list"],
            {"file": upload, "instructor": instructor.id},
            format="multipart",
        )
        assert response.status_code == 400
        assert "file" in response.data

    def test_rejects_oversized_file(self, auth_client, course, syllabus_urls):
        instructor = _offering_with_instructor(course)
        upload = SimpleUploadedFile(
            "big.pdf", b"x" * 21 * 1024 * 1024, content_type="application/pdf"
        )
        response = auth_client.post(
            syllabus_urls["list"],
            {"file": upload, "instructor": instructor.id},
            format="multipart",
        )
        assert response.status_code == 400

    def test_rejects_instructor_not_teaching_course(
        self, auth_client, course, syllabus_urls
    ):
        stranger = InstructorFactory()
        upload = _make_pdf_upload()
        response = auth_client.post(
            syllabus_urls["list"],
            {"file": upload, "instructor": stranger.id},
            format="multipart",
        )
        assert response.status_code == 400

    def test_successful_upload_analyzes_and_stores_by_hash(
        self,
        auth_client,
        course,
        user,
        syllabus_urls,
        fake_ollama,
        fake_extraction,
    ):
        instructor = _offering_with_instructor(course)
        upload = _make_pdf_upload()
        response = auth_client.post(
            syllabus_urls["list"],
            {"file": upload, "instructor": instructor.id},
            format="multipart",
        )
        assert response.status_code == 201
        data = response.data
        assert data["status"] == Syllabus.Status.ANALYZED  # eager task ran
        assert data["is_primary"] is True
        assert data["uploaded_by"] == user.username
        assert "Summary" in data["summary_md"]
        assert data["verdict"]["match_score"] == 88

        stored = SyllabusFile.objects.get(pk=data["file"]["id"])
        assert stored is not None
        assert len(stored.sha256) == 64  # sha256 of the uploaded bytes

        # Stored under the <sha256>.pdf name and scoped to the test media root
        assert stored.file.name.startswith("syllabi/")
        assert stored.file.name.endswith(".pdf")

    def test_same_bytes_share_file_different_syllabus_rows(
        self, auth_client, course, syllabus_urls, fake_ollama, fake_extraction
    ):
        instructor_a = _offering_with_instructor(course)
        instructor_b = InstructorFactory()
        offering_b = CourseOfferingFactory(course=course)
        offering_b.instructors.add(instructor_b)

        # Fresh upload object per POST — a consumed SimpleUploadedFile can't
        # be re-encoded by the multipart client.
        first = auth_client.post(
            syllabus_urls["list"],
            {"file": _make_pdf_upload(), "instructor": instructor_a.id},
            format="multipart",
        )
        second = auth_client.post(
            syllabus_urls["list"],
            {"file": _make_pdf_upload(), "instructor": instructor_b.id},
            format="multipart",
        )
        assert first.status_code == second.status_code == 201
        assert first.data["file"]["id"] == second.data["file"]["id"]
        assert first.data["id"] != second.data["id"]
        assert SyllabusFile.objects.count() == 1
        assert Syllabus.objects.count() == 2

    def test_identical_reupload_is_idempotent(
        self, auth_client, course, syllabus_urls, fake_ollama, fake_extraction
    ):
        instructor = _offering_with_instructor(course)
        first = auth_client.post(
            syllabus_urls["list"],
            {"file": _make_pdf_upload(), "instructor": instructor.id},
            format="multipart",
        )
        second = auth_client.post(
            syllabus_urls["list"],
            {"file": _make_pdf_upload(), "instructor": instructor.id},
            format="multipart",
        )
        assert first.status_code == 201
        assert second.status_code == 200
        assert first.data["id"] == second.data["id"]
        assert Syllabus.objects.count() == 1


# ---------------------------------------------------------------------------
# List / detail / download
# ---------------------------------------------------------------------------


class TestRead:
    def test_list_is_public(self, base_client, syllabus_urls):
        response = base_client.get(syllabus_urls["list"])
        assert response.status_code == 200

    def test_second_version_triggers_comparison_and_primary_handover(
        self, auth_client, course, syllabus_urls, fake_ollama, fake_extraction
    ):
        instructor = _offering_with_instructor(course)
        first = auth_client.post(
            syllabus_urls["list"],
            {
                "file": _make_pdf_upload(content=b"%PDF v1", name="v1.pdf"),
                "instructor": instructor.id,
            },
            format="multipart",
        )
        assert first.data["is_primary"] is True

        second = auth_client.post(
            syllabus_urls["list"],
            {
                "file": _make_pdf_upload(content=b"%PDF v2 longer", name="v2.pdf"),
                "instructor": instructor.id,
            },
            format="multipart",
        )
        assert second.status_code == 201
        # Mock comparison recommends keep_new -> primary handover
        assert second.data["is_primary"] is True
        assert second.data["comparison"]["recommendation"] == "keep_new"
        assert Syllabus.objects.get(pk=first.data["id"]).is_primary is False

    def test_download_requires_login(
        self, base_client, auth_client, user, course, syllabus_urls
    ):
        instructor = _offering_with_instructor(course)
        syllabus = SyllabusFactory(
            course=course, instructor=instructor, uploaded_by=user
        )
        anon = APIClient()  # base_client is shared with auth_client
        response = anon.get(syllabus_urls["download"](syllabus.id))
        assert response.status_code in (401, 403)
        authed = auth_client.get(syllabus_urls["download"](syllabus.id))
        assert authed.status_code == 200
        assert "attachment" in authed["Content-Disposition"]
        streamed = b"".join(authed.streaming_content)
        assert streamed == syllabus.file.file.read()

    def test_staff_patch_clears_sibling_primary(
        self, auth_client, staff_client, user, course, syllabus_urls
    ):
        instructor = _offering_with_instructor(course)
        primary = SyllabusFactory(
            course=course, instructor=instructor, uploaded_by=user, is_primary=True
        )
        other = SyllabusFactory(
            course=course, instructor=instructor, uploaded_by=user, is_primary=False
        )
        # Non-staff cannot patch
        denied = auth_client.patch(
            syllabus_urls["detail"](other.id),
            {"summary_md": "hacked", "is_primary": True},
            format="json",
        )
        assert denied.status_code == 403

        updated = staff_client.patch(
            syllabus_urls["detail"](other.id),
            {"summary_md": "Curated by admin", "is_primary": True},
            format="json",
        )
        assert updated.status_code == 200
        primary.refresh_from_db()
        other.refresh_from_db()
        assert primary.is_primary is False
        assert other.is_primary is True
        assert other.summary_md == "Curated by admin"


# ---------------------------------------------------------------------------
# Task failure + OCR path
# ---------------------------------------------------------------------------


class TestTaskEdgeCases:
    def test_ollama_failure_marks_syllabus_failed(
        self, auth_client, course, syllabus_urls, fake_extraction, monkeypatch
    ):
        from apps.web.syllabus_analysis import SyllabusAnalysisError

        instructor = _offering_with_instructor(course)

        def _chat_down(messages, format_json=False):
            raise SyllabusAnalysisError("model down")

        monkeypatch.setattr("apps.web.syllabus_analysis.ollama_chat", _chat_down)
        upload = _make_pdf_upload()
        response = auth_client.post(
            syllabus_urls["list"],
            {"file": upload, "instructor": instructor.id},
            format="multipart",
        )
        assert response.status_code == 201
        syllabus = Syllabus.objects.get(pk=response.data["id"])
        assert syllabus.status == Syllabus.Status.FAILED
        assert "model down" in syllabus.error_message

    def test_ocr_path_called_for_textless_pdf(
        self, auth_client, course, syllabus_urls, fake_ollama, monkeypatch
    ):
        instructor = _offering_with_instructor(course)

        calls = {}

        def fake_extract(content: bytes) -> str:
            calls["extract"] = True
            return ""

        def fake_render(content: bytes, max_pages=None):
            calls["render"] = True
            return [b"fake-png-page"]

        def fake_ocr(images):
            calls["ocr"] = True
            return "OCR'd syllabus text"

        import apps.web.tasks as tasks_mod

        monkeypatch.setattr(tasks_mod, "extract_pdf_text", fake_extract)
        monkeypatch.setattr(tasks_mod, "render_pdf_pages", fake_render)
        monkeypatch.setattr(tasks_mod, "ocr_pages", fake_ocr)
        upload = _make_pdf_upload()
        response = auth_client.post(
            syllabus_urls["list"],
            {"file": upload, "instructor": instructor.id},
            format="multipart",
        )
        assert response.status_code == 201
        assert calls.get("extract") and calls.get("render") and calls.get("ocr")
        syllabus = Syllabus.objects.get(pk=response.data["id"])
        assert syllabus.status == Syllabus.Status.ANALYZED
        assert "OCR'd" in syllabus.file.extracted_text


# ---------------------------------------------------------------------------
# Instructor serialization + staff flag
# ---------------------------------------------------------------------------


class TestPayloads:
    def test_course_instructors_endpoint_returns_objects(self, base_client, course):
        instructor = _offering_with_instructor(course)
        url = reverse("course_instructors", kwargs={"course_id": course.id})
        response = base_client.get(url)
        assert response.status_code == 200
        assert {"id": instructor.id, "name": instructor.name} in response.data[
            "instructors"
        ]

    def test_course_detail_instructors_are_objects(self, base_client, course):
        instructor = _offering_with_instructor(course)
        url = reverse("course_detail_api", kwargs={"course_id": course.id})
        response = base_client.get(url)
        assert response.status_code == 200
        instructors = response.data["instructors"]
        assert any(i["id"] == instructor.id for i in instructors)
        assert all(isinstance(i, dict) for i in instructors)

    def test_user_status_exposes_staff(self, auth_client, staff_client):
        response = auth_client.get(reverse("user_status"))
        assert response.data["is_staff"] is False
        response = staff_client.get(reverse("user_status"))
        assert response.data["is_staff"] is True
        anonymous = APIClient()
        response = anonymous.get(reverse("user_status"))
        assert response.data["isAuthenticated"] is False
