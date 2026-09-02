import csv
from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.web.management.commands.import_legacy_reviews import IMPORT_USERNAME
from apps.web.models import Course, Review


HEADERS = ["course_code", "professor", "term", "comment"]


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def row(course_code="TEST1000J", professor="Professor", term="", comment="Comment"):
    return {
        "course_code": course_code,
        "professor": professor,
        "term": term,
        "comment": comment,
    }


@pytest.mark.django_db
def test_actual_csv_has_expected_eligible_count():
    command = __import__(
        "apps.web.management.commands.import_legacy_reviews",
        fromlist=["Command"],
    ).Command()

    rows, total, skipped = command._read_csv(
        __import__("pathlib").Path("data/legacy_reviews.csv")
    )

    assert total == 350
    assert skipped == 11
    assert len(rows) == 339


@pytest.mark.django_db
def test_dry_run_skips_missing_professor_and_writes_nothing(tmp_path):
    Course.objects.create(course_code="TEST1000J")
    rows = [row(comment=f"Comment {index}") for index in range(339)]
    rows.extend(row(professor="", comment=f"Skipped {index}") for index in range(11))
    csv_path = write_csv(tmp_path / "reviews.csv", rows)
    stdout = StringIO()

    call_command("import_legacy_reviews", csv_path, stdout=stdout)

    assert "CSV total: 350" in stdout.getvalue()
    assert "Skipped missing professor: 11" in stdout.getvalue()
    assert "Eligible: 339" in stdout.getvalue()
    assert Review.objects.count() == 0
    assert not User.objects.filter(username=IMPORT_USERNAME).exists()


@pytest.mark.django_db
def test_unmatched_course_aborts_without_writes(tmp_path):
    csv_path = write_csv(tmp_path / "reviews.csv", [row(course_code="MISSING")])

    with pytest.raises(CommandError, match="unmatched"):
        call_command("import_legacy_reviews", csv_path, expected_count=1)

    assert Review.objects.count() == 0
    assert not User.objects.filter(username=IMPORT_USERNAME).exists()


@pytest.mark.django_db
def test_execute_is_required_to_insert_and_preserves_blank_term(tmp_path):
    course = Course.objects.create(course_code="TEST1000J")
    csv_path = write_csv(tmp_path / "reviews.csv", [row(term="")])

    call_command("import_legacy_reviews", csv_path, expected_count=1)
    assert Review.objects.count() == 0

    call_command("import_legacy_reviews", csv_path, expected_count=1, execute=True)
    review = Review.objects.get()
    assert review.course == course
    assert review.term == ""


@pytest.mark.django_db
def test_execute_creates_inactive_unusable_import_user(tmp_path):
    Course.objects.create(course_code="TEST1000J")
    csv_path = write_csv(tmp_path / "reviews.csv", [row()])

    call_command("import_legacy_reviews", csv_path, expected_count=1, execute=True)

    user = User.objects.get(username=IMPORT_USERNAME)
    assert user.is_active is False
    assert user.has_usable_password() is False


@pytest.mark.django_db
def test_duplicate_csv_rows_and_repeated_runs_do_not_duplicate(tmp_path):
    Course.objects.create(course_code="TEST1000J")
    csv_path = write_csv(tmp_path / "reviews.csv", [row(), row()])

    call_command("import_legacy_reviews", csv_path, expected_count=2, execute=True)
    call_command("import_legacy_reviews", csv_path, expected_count=2, execute=True)

    assert Review.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_bulk_insert_failure_rolls_back_everything(tmp_path, monkeypatch):
    Course.objects.create(course_code="TEST1000J")
    csv_path = write_csv(
        tmp_path / "reviews.csv",
        [row(comment="First"), row(comment="Second")],
    )

    def fail_bulk_create(*args, **kwargs):
        Review.objects.create(
            course=Course.objects.get(course_code="TEST1000J"),
            user=User.objects.get(username=IMPORT_USERNAME),
            professor="Professor",
            term="",
            comments="Partial write",
        )
        raise RuntimeError("simulated insert failure")

    monkeypatch.setattr(Review.objects, "bulk_create", fail_bulk_create)

    with pytest.raises(RuntimeError, match="simulated insert failure"):
        call_command("import_legacy_reviews", csv_path, expected_count=2, execute=True)

    assert Review.objects.count() == 0
    assert not User.objects.filter(username=IMPORT_USERNAME).exists()


@pytest.mark.django_db
def test_wrong_eligible_count_aborts_before_writes(tmp_path):
    Course.objects.create(course_code="TEST1000J")
    csv_path = write_csv(tmp_path / "reviews.csv", [row()])

    with pytest.raises(CommandError, match="expected 339"):
        call_command("import_legacy_reviews", csv_path)

    assert Review.objects.count() == 0
