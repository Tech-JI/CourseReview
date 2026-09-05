import logging

from celery import shared_task
from django.db import transaction

from apps.web.models import Syllabus, SyllabusFile
from apps.web.syllabus_analysis import (
    TEXT_OCR_THRESHOLD,
    SyllabusAnalysisError,
    analyze,
    compare,
    extract_docx_text,
    extract_pdf_text,
    ocr_pages,
    render_pdf_pages,
)

logger = logging.getLogger(__name__)


@shared_task
def process_syllabus(syllabus_id):
    """Extract text, analyze against course data, and resolve the primary copy.

    Never deletes files: every upload is kept; comparison only decides which
    of the duplicates is marked primary.

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
    summary_md = str(verdict.get("summary_md", "")).strip()
    if not summary_md:
        raise SyllabusAnalysisError("Model returned no summary")

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
    file_obj.extracted_text = text
    file_obj.save(update_fields=["extracted_text", "updated_at"])
    return text
