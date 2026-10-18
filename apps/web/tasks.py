import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction

from apps.web.models import Syllabus, SyllabusFile
from apps.web.syllabus_files import purge_recycled_files, recycle_file_if_unreferenced
from apps.web.markdown_clean import sanitize_markdown
from apps.web.syllabus_analysis import (
    TEXT_OCR_THRESHOLD,
    SyllabusAnalysisError,
    analyze,
    compare,
    extract_docx_text,
    extract_pdf_text,
    has_course_signal,
    max_extracted_chars,
    ocr_pages,
    render_pdf_pages,
    verify_evidence,
)

logger = logging.getLogger(__name__)


@shared_task
def process_syllabus(syllabus_id):
    """Extract text, analyze against course data, and resolve the primary copy.

    Uploads whose verdict match_score is below the configured threshold are
    rejected (status ``rejected``, kept for audit, hidden from course pages)
    and their file moved to the recycle dir when no other syllabus shares it.
    Comparison only decides which of the duplicates is marked primary.

    Failure bookkeeping lives outside the atomic block: a raise inside it
    would roll the FAILED status back with the rest of the work.
    """
    try:
        _analyze_and_resolve(syllabus_id)
    except Exception as exc:  # noqa: BLE001 - any failure marks the syllabus failed
        logger.exception("Syllabus analysis failed for syllabus %s", syllabus_id)
        Syllabus.objects.filter(pk=syllabus_id).update(
            status=Syllabus.Status.FAILED, error_message=str(exc)[:1000]
        )
        raise


@transaction.atomic
def _analyze_and_resolve(syllabus_id):
    syllabus = (
        Syllabus.objects.select_for_update()
        .select_related("file", "course", "instructor")
        .get(pk=syllabus_id)
    )
    syllabus.status = Syllabus.Status.PROCESSING
    syllabus.save(update_fields=["status", "updated_at"])

    text = _extract_or_ocr(syllabus.file)
    siblings = list(
        Syllabus.objects.filter(
            course=syllabus.course,
            instructor=syllabus.instructor,
            status=Syllabus.Status.ANALYZED,
        )
        .exclude(pk=syllabus.pk)
        .order_by("-created_at")
    )
    verdict = analyze(syllabus.course, syllabus.instructor, text)
    verdict = verify_evidence(
        verdict, text, require_evidence=settings.SYLLABUS["REQUIRE_EVIDENCE"]
    )
    summary_md = sanitize_markdown(str(verdict.get("summary_md", "")).strip())
    if not summary_md:
        raise SyllabusAnalysisError("Model returned no summary")

    # Reject uploads that clearly do not belong to this course: keep the row
    # for audit (admin can still see and restore it) but hide it from the
    # course page, and recycle the file once nothing references it.
    match_score = verdict.get("match_score")
    low_score = isinstance(match_score, (int, float)) and (
        match_score < settings.SYLLABUS["MIN_MATCH_SCORE"]
    )
    # A verdict that quotes text the document never contains, or a document
    # with no sign of the course at all, is not trusted regardless of score.
    untrusted = bool(verdict.get("evidence_unverified")) or (
        settings.SYLLABUS["REQUIRE_COURSE_SIGNAL"]
        and not has_course_signal(text, syllabus.course, syllabus.instructor)
    )
    if low_score or untrusted:
        syllabus.summary_md = summary_md
        syllabus.verdict = verdict
        syllabus.status = Syllabus.Status.REJECTED
        syllabus.error_message = ""
        syllabus.save()
        recycle_file_if_unreferenced(syllabus.file, exclude_syllabus=syllabus)
        return

    syllabus.summary_md = summary_md
    syllabus.verdict = verdict
    syllabus.status = Syllabus.Status.ANALYZED
    syllabus.error_message = ""
    syllabus.save()

    if not siblings:
        syllabus.is_primary = True
        syllabus.save(update_fields=["is_primary", "updated_at"])
        return

    # Compare against the current primary sibling (if still one).
    primary_sibling = next((s for s in siblings if s.is_primary), siblings[0])
    comparison = compare(
        syllabus.course,
        syllabus.instructor,
        text,
        primary_sibling.file.extracted_text,
    )
    syllabus.comparison = comparison
    syllabus.save(update_fields=["comparison", "updated_at"])
    if comparison.get("recommendation") == "keep_new":
        primary_sibling.is_primary = False
        primary_sibling.save(update_fields=["is_primary", "updated_at"])
        syllabus.is_primary = True
        syllabus.save(update_fields=["is_primary", "updated_at"])


def _extract_or_ocr(file_obj: SyllabusFile) -> str:
    """Return extracted text, using the cached copy when present."""
    if file_obj.extracted_text:
        return file_obj.extracted_text
    with file_obj.file.open("rb") as handle:
        content = handle.read()
    name = file_obj.file.name.lower()
    if name.endswith(".pdf"):
        text = extract_pdf_text(content)
        if len(text.strip()) < TEXT_OCR_THRESHOLD:
            logger.info("PDF %s looks scanned; OCR via vision model", file_obj.pk)
            images = render_pdf_pages(content)
            text = ocr_pages(images)
    elif name.endswith(".docx"):
        text = extract_docx_text(content)
    else:
        raise SyllabusAnalysisError(f"Unsupported syllabus file type: {name}")

    if len(text.strip()) < 10:
        raise SyllabusAnalysisError("Could not extract any readable text from the file")
    limit = max_extracted_chars()
    if len(text) > limit:
        text = text[:limit]
    file_obj.extracted_text = text
    file_obj.save(update_fields=["extracted_text", "updated_at"])
    return text


@shared_task
def purge_recycled_syllabus_files():
    """Sweep the recycle dir so soft-deleted syllabus files have a TTL."""
    purged = purge_recycled_files()
    if purged:
        logger.info("Purged %d recycled syllabus files", purged)
    return purged
