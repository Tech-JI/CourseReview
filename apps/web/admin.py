import hashlib
import os
from io import StringIO
from tempfile import NamedTemporaryFile

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.shortcuts import render
from django.urls import path

from .models import (
    Course,
    CourseMedian,
    CourseOffering,
    DistributiveRequirement,
    Instructor,
    Review,
    ReviewVote,
    Student,
    Vote,
)

admin.site.register(Course)
admin.site.register(CourseOffering)
admin.site.register(DistributiveRequirement)
admin.site.register(Instructor)
admin.site.register(CourseMedian)


class LegacyReviewUploadForm(forms.Form):
    csv_file = forms.FileField(label="Legacy review CSV")
    expected_count = forms.IntegerField(min_value=0, initial=339)


class ReviewAdmin(admin.ModelAdmin):
    change_list_template = "admin/web/review/change_list.html"
    preview_session_key = "legacy_review_import_preview"
    max_upload_size = 1024 * 1024

    def get_urls(self):
        custom_urls = [
            path(
                "import-legacy-reviews/",
                self.admin_site.admin_view(self.import_legacy_reviews_view),
                name="web_review_import_legacy_reviews",
            )
        ]
        return custom_urls + super().get_urls()

    def import_legacy_reviews_view(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can import legacy reviews.")

        context = {
            **self.admin_site.each_context(request),
            "title": "Import legacy reviews",
            "opts": self.model._meta,
        }

        if request.method == "POST" and request.POST.get("action") == "execute":
            preview = request.session.get(self.preview_session_key)
            if not preview:
                context["error"] = "Run a dry-run with a CSV before importing."
                context["upload_form"] = LegacyReviewUploadForm()
                return render(
                    request, "admin/web/review/import_legacy_reviews.html", context
                )

            output, error = self._run_import(
                preview["csv_text"], preview["expected_count"], execute=True
            )
            context["output"] = output
            context["error"] = error
            context["upload_form"] = LegacyReviewUploadForm(
                initial={"expected_count": preview["expected_count"]}
            )
            if not error:
                del request.session[self.preview_session_key]
            return render(
                request, "admin/web/review/import_legacy_reviews.html", context
            )

        if request.method == "POST":
            form = LegacyReviewUploadForm(request.POST, request.FILES)
            context["upload_form"] = form
            if form.is_valid():
                upload = form.cleaned_data["csv_file"]
                if upload.size > self.max_upload_size:
                    form.add_error("csv_file", "CSV files must be no larger than 1 MiB.")
                else:
                    try:
                        csv_text = upload.read().decode("utf-8-sig")
                    except UnicodeDecodeError:
                        form.add_error("csv_file", "CSV must be UTF-8 encoded.")
                    else:
                        expected_count = form.cleaned_data["expected_count"]
                        output, error = self._run_import(
                            csv_text, expected_count, execute=False
                        )
                        context["output"] = output
                        context["error"] = error
                        if not error:
                            request.session[self.preview_session_key] = {
                                "csv_text": csv_text,
                                "expected_count": expected_count,
                                "sha256": hashlib.sha256(
                                    csv_text.encode("utf-8")
                                ).hexdigest(),
                            }
                            context["preview_ready"] = True
            return render(
                request, "admin/web/review/import_legacy_reviews.html", context
            )

        context["upload_form"] = LegacyReviewUploadForm()
        return render(request, "admin/web/review/import_legacy_reviews.html", context)

    def _run_import(self, csv_text, expected_count, *, execute):
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", suffix=".csv", delete=False
        ) as csv_file:
            csv_file.write(csv_text)
            csv_path = csv_file.name

        stdout = StringIO()
        stderr = StringIO()
        try:
            call_command(
                "import_legacy_reviews",
                csv_path,
                expected_count=expected_count,
                execute=execute,
                stdout=stdout,
                stderr=stderr,
            )
        except CommandError as exc:
            error = str(exc)
        else:
            error = stderr.getvalue().strip() or None
        finally:
            os.unlink(csv_path)

        return stdout.getvalue(), error


admin.site.register(Review, ReviewAdmin)
admin.site.register(ReviewVote)
admin.site.register(Vote)
admin.site.register(Student)
