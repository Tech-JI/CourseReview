from __future__ import unicode_literals

from django.conf import settings
from django.db import models


class Syllabus(models.Model):
    """A syllabus uploaded for one course + instructor pairing.

    `file` points at a shared SyllabusFile (deduped by sha256). The AI
    analysis writes `summary_md`, `verdict` and `comparison`; exactly one
    analyzed Syllabus per (course, instructor) is `is_primary`.
    """

    class Status:
        PENDING = "pending"
        PROCESSING = "processing"
        ANALYZED = "analyzed"
        FAILED = "failed"

    STATUS_CHOICES = [
        (Status.PENDING, "Pending"),
        (Status.PROCESSING, "Processing"),
        (Status.ANALYZED, "Analyzed"),
        (Status.FAILED, "Failed"),
    ]

    course = models.ForeignKey(
        "Course", on_delete=models.CASCADE, related_name="syllabi"
    )
    instructor = models.ForeignKey(
        "Instructor", on_delete=models.CASCADE, related_name="syllabi"
    )
    file = models.ForeignKey(
        "SyllabusFile", on_delete=models.PROTECT, related_name="syllabi"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_syllabi",
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=Status.PENDING, db_index=True
    )
    summary_md = models.TextField(blank=True, default="")
    verdict = models.JSONField(null=True, blank=True)
    comparison = models.JSONField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "instructor", "file"],
                name="unique_course_instructor_syllabus_file",
            )
        ]
        indexes = [models.Index(fields=["course", "instructor", "status"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course_id} / {self.instructor_id} / {self.status}"
