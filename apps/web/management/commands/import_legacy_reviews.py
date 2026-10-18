import csv
import os
from dataclasses import dataclass, replace
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.web.models import Course, Instructor, Review
from lib.name_normalization import canonicalize_professor


IMPORT_USERNAME = "LegacyReviewImporter"
REQUIRED_COLUMNS = {"course_code", "professor", "term", "comment"}


@dataclass(frozen=True)
class LegacyReviewRow:
    course_code: str
    professor: str
    term: str
    comments: str

    @property
    def duplicate_key(self):
        return (self.course_code, self.professor, self.comments)


class Command(BaseCommand):
    help = "Safely import anonymous legacy reviews (dry-run unless --execute is used)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)
        parser.add_argument("--expected-count", type=int, default=339)
        parser.add_argument("--execute", action="store_true")

    def handle(self, *args, **options):
        self._check_database()
        rows, total, skipped_missing_professor = self._read_csv(options["csv_path"])
        eligible = len(rows)

        if eligible != options["expected_count"]:
            self._write_stats(
                total=total,
                skipped_missing_professor=skipped_missing_professor,
                eligible=eligible,
            )
            raise CommandError(
                f"Eligible count is {eligible}, expected {options['expected_count']}; aborting."
            )

        course_codes = sorted({row.course_code for row in rows})
        courses = {}
        unmatched = []
        for course_code in course_codes:
            try:
                courses[course_code] = Course.objects.get(course_code=course_code)
            except Course.DoesNotExist:
                unmatched.append(course_code)

        # Canonicalize legacy professor names against each course's instructors
        # (same matching rules as the review-submission path) so reversed /
        # misspelled CSV variants land on the canonical name and dedupe
        # correctly against both the CSV and the database.
        course_instructor_names = {
            code: list(
                Instructor.objects.filter(courseoffering__course=course)
                .values_list("name", flat=True)
                .distinct()
            )
            for code, course in courses.items()
        }
        canonical_rows = []
        for row in rows:
            if row.course_code not in courses:
                canonical_rows.append(row)
                continue
            canonical = canonicalize_professor(
                row.professor, course_instructor_names[row.course_code]
            )
            canonical_rows.append(replace(row, professor=canonical or row.professor))

        unique_rows = []
        seen = set()
        duplicate_in_csv = 0
        for row in canonical_rows:
            if row.duplicate_key in seen:
                duplicate_in_csv += 1
                continue
            seen.add(row.duplicate_key)
            unique_rows.append(row)

        matched_rows = [row for row in unique_rows if row.course_code in courses]
        unmatched_rows = [row for row in unique_rows if row.course_code not in courses]
        # A review already exists if any row for the same course carries the
        # same comment text. Legacy comments are unique per (course, comment)
        # (verified for the shipped CSV), and professor spellings were
        # consolidated to canonical names after import — so matching on the
        # exact professor string would re-insert duplicate comments whose CSV
        # variant did not machine-canonicalize (e.g. single-word "Manuel").
        existing_keys = set()
        for row in matched_rows:
            if Review.objects.filter(
                course=courses[row.course_code],
                comments=row.comments,
            ).exists():
                existing_keys.add(row.duplicate_key)

        pending = [
            row for row in matched_rows if row.duplicate_key not in existing_keys
        ]
        self._write_stats(
            total=total,
            skipped_missing_professor=skipped_missing_professor,
            eligible=eligible,
            unique_course_codes=len(course_codes),
            matched_courses=len(courses),
            unmatched=unmatched,
            unmatched_reviews=len(unmatched_rows),
            duplicate_in_csv=duplicate_in_csv,
            already_in_database=len(existing_keys),
            pending_inserts=len(pending),
        )

        if unmatched:
            self.stdout.write("Unmatched course codes (kept in CSV, not imported):")
            for course_code in unmatched:
                self.stdout.write(f"  {course_code}")

        if not options["execute"]:
            self.stdout.write(self.style.WARNING("DRY-RUN only; no data was written."))
            return

        if pending:
            with transaction.atomic():
                user = self._get_import_user()
                Review.objects.bulk_create(
                    [
                        Review(
                            course=courses[row.course_code],
                            user=user,
                            professor=row.professor,
                            term=row.term,
                            comments=row.comments,
                        )
                        for row in pending
                    ]
                )

        self.stdout.write(self.style.SUCCESS(f"Inserted reviews: {len(pending)}"))
        self.stdout.write(
            f"Deduplicated/skipped: {duplicate_in_csv + len(existing_keys)}"
        )

    def _check_database(self):
        if not os.environ.get("DATABASE__URL"):
            raise CommandError(
                "DATABASE__URL is not set; refusing to use a fallback database."
            )
        if connection.vendor != "postgresql":
            raise CommandError(
                "Configured database is not PostgreSQL; refusing to continue."
            )
        try:
            connection.ensure_connection()
        except Exception as exc:
            raise CommandError(
                "Unable to connect to the configured PostgreSQL database."
            ) from exc

    def _read_csv(self, csv_path):
        if not csv_path.is_file():
            raise CommandError(f"CSV file does not exist: {csv_path}")

        rows = []
        skipped_missing_professor = 0
        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or ())
            if missing_columns:
                raise CommandError(
                    "CSV is missing required columns: "
                    + ", ".join(sorted(missing_columns))
                )
            total = 0
            for record in reader:
                total += 1
                professor = record["professor"].strip()
                if not professor:
                    skipped_missing_professor += 1
                    continue
                rows.append(
                    LegacyReviewRow(
                        course_code=record["course_code"].strip(),
                        professor=professor,
                        term=record["term"].strip(),
                        comments=record["comment"],
                    )
                )
        return rows, total, skipped_missing_professor

    def _get_import_user(self):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=IMPORT_USERNAME,
            defaults={"is_active": False},
        )
        changed = created
        if user.is_active:
            user.is_active = False
            changed = True
        if user.has_usable_password():
            user.set_unusable_password()
            changed = True
        if changed:
            user.save(update_fields=["is_active", "password"])
        return user

    def _write_stats(
        self,
        *,
        total,
        skipped_missing_professor,
        eligible,
        unique_course_codes=0,
        matched_courses=0,
        unmatched=(),
        unmatched_reviews=0,
        duplicate_in_csv=0,
        already_in_database=0,
        pending_inserts=0,
    ):
        db = connection.settings_dict
        lines = [
            f"CSV total: {total}",
            f"Skipped missing professor: {skipped_missing_professor}",
            f"Eligible: {eligible}",
            f"Unique course codes: {unique_course_codes}",
            f"Matched courses: {matched_courses}",
            f"Unmatched courses: {len(unmatched)}",
            f"Skipped unmatched reviews: {unmatched_reviews}",
            f"Duplicate in CSV: {duplicate_in_csv}",
            f"Already in database: {already_in_database}",
            f"Pending inserts: {pending_inserts}",
            f"Database engine: {db.get('ENGINE', '')}",
            f"Database host: {db.get('HOST') or '<default>'}",
            f"Database port: {db.get('PORT') or '<default>'}",
            f"Database name: {db.get('NAME') or '<default>'}",
        ]
        self.stdout.write("\n".join(lines))
