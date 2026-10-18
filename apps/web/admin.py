import hashlib
import json
import os
from io import StringIO
from tempfile import NamedTemporaryFile

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html

from .models import (
    Course,
    CourseMedian,
    CourseOffering,
    DistributiveRequirement,
    Instructor,
    Review,
    ReviewVote,
    Student,
    Syllabus,
    SyllabusFile,
    Vote,
)
from .markdown_clean import sanitize_markdown
from .syllabus_files import recycle_file_if_unreferenced

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
                    form.add_error(
                        "csv_file", "CSV files must be no larger than 1 MiB."
                    )
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


@admin.register(SyllabusFile)
class SyllabusFileAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "sha256", "size", "created_at")
    search_fields = ("original_filename", "sha256")
    readonly_fields = ("sha256", "original_filename", "size", "created_at")
    fields = ("file", "sha256", "original_filename", "size", "content_type")


@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    change_form_template = "admin/web/syllabus/change_form.html"
    list_display = (
        "id",
        "course",
        "instructor",
        "status",
        "is_primary",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("status", "is_primary")
    search_fields = ("course__course_code", "course__course_title", "instructor__name")
    actions = ("reject_syllabi",)
    readonly_fields = (
        "analysis_display",
        "comparison_display",
        "created_at",
        "updated_at",
    )
    fields = (
        "course",
        "instructor",
        "file",
        "status",
        "is_primary",
        "summary_md",
        "analysis_display",
        "comparison_display",
        "error_message",
        "uploaded_by",
        "created_at",
        "updated_at",
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        form_field = super().formfield_for_dbfield(db_field, **kwargs)
        if isinstance(db_field, models.TextField) and db_field.name == "summary_md":
            form_field.widget = forms.Textarea(attrs={"rows": 10, "cols": 80})
        return form_field

    @admin.display(description="Analysis verdict")
    def analysis_display(self, obj):
        if not obj.verdict:
            return "—"
        return format_html(
            '<pre style="white-space: pre-wrap; margin: 0;">{}</pre>',
            json.dumps(obj.verdict, indent=2, ensure_ascii=False),
        )

    @admin.display(description="Version comparison")
    def comparison_display(self, obj):
        if not obj.comparison:
            return "—"
        return format_html(
            '<pre style="white-space: pre-wrap; margin: 0;">{}</pre>',
            json.dumps(obj.comparison, indent=2, ensure_ascii=False),
        )

    def save_model(self, request, obj, form, change):
        obj.summary_md = sanitize_markdown(obj.summary_md)
        super().save_model(request, obj, form, change)
        if obj.is_primary:
            Syllabus.objects.filter(
                course=obj.course, instructor=obj.instructor
            ).exclude(pk=obj.pk).update(is_primary=False)

    def _mark_rejected(self, syllabus):
        syllabus.status = Syllabus.Status.REJECTED
        syllabus.is_primary = False
        syllabus.save(update_fields=["status", "is_primary", "updated_at"])
        recycle_file_if_unreferenced(syllabus.file, exclude_syllabus=syllabus)

    def response_change(self, request, obj):
        if "_reject" in request.POST:
            self._mark_rejected(obj)
            self.message_user(request, f"Syllabus {obj.pk} rejected.")
            return HttpResponseRedirect(request.path)
        return super().response_change(request, obj)

    @admin.action(description="Reject selected syllabi (mark rejected, unset primary)")
    def reject_syllabi(self, request, queryset):
        for syllabus in queryset.select_related("file"):
            self._mark_rejected(syllabus)
