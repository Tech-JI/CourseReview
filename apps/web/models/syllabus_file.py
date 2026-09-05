from __future__ import unicode_literals

from django.db import models


class SyllabusFile(models.Model):
    """One uploaded syllabus document, deduplicated by content sha256.

    The same file (identical bytes) uploaded for different courses or
    instructors shares a single SyllabusFile row; `extracted_text` is cached
    here so re-analysis never re-extracts or re-OCRs.
    """

    file = models.FileField(upload_to="syllabi/")
    sha256 = models.CharField(max_length=64, unique=True, db_index=True)
    content_type = models.CharField(max_length=100, blank=True, default="")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    size = models.PositiveBigIntegerField(default=0)
    extracted_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sha256[:16]
