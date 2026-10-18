"""Filesystem helpers for syllabus files: recycle (soft-delete) storage.

Files live in MEDIA_ROOT/syllabi/<sha256>.<ext> and are shared by
Syllabus rows via sha256 dedup. When the last referencing syllabus is
rejected or deleted the file moves to MEDIA_ROOT/recycle/ instead of
being destroyed, so an admin can audit and restore it.
"""

from __future__ import unicode_literals

import os
import shutil
import logging
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.files.storage import default_storage

from apps.web.models import Syllabus, SyllabusFile

logger = logging.getLogger(__name__)

RECYCLE_DIR = "recycle"
UPLOAD_DIR = "syllabi"

ACTIVE_SYLLABUS_STATUSES = (
    Syllabus.Status.PENDING,
    Syllabus.Status.PROCESSING,
    Syllabus.Status.ANALYZED,
)


def recycle_file_if_unreferenced(file_obj, exclude_syllabus=None):
    """Move ``file_obj`` (a SyllabusFile row) to the recycle dir if orphaned.

    A file counts as referenced when any Syllabus other than
    ``exclude_syllabus`` still points at it; callers pass the syllabus being
    rejected/deleted so its own reference does not block the move. Returns
    the new relative name, or None when nothing was moved.
    """
    referencing = file_obj.syllabi.all()
    if exclude_syllabus is not None:
        referencing = referencing.exclude(pk=exclude_syllabus.pk)
    if referencing.exists():
        return None

    storage = default_storage
    current_name = file_obj.file.name
    if not current_name or current_name.startswith(f"{RECYCLE_DIR}/"):
        return None

    base = current_name.rsplit("/", 1)[-1]
    dest_name = f"{RECYCLE_DIR}/{base}"
    if storage.exists(dest_name):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        dest_name = f"{RECYCLE_DIR}/{stamp}_{base}"

    if hasattr(storage, "path"):
        dest_dir = os.path.dirname(storage.path(dest_name))
        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(storage.path(current_name), storage.path(dest_name))
    else:
        storage.save(dest_name, file_obj.file)  # remote fallback
        storage.delete(current_name)

    file_obj.file.name = dest_name
    file_obj.save(update_fields=["file", "updated_at"])
    return dest_name


def restore_recycled_file(file_obj):
    storage = default_storage
    current_name = file_obj.file.name
    if not current_name or not current_name.startswith(f"{RECYCLE_DIR}/"):
        return current_name

    base = current_name.rsplit("/", 1)[-1]
    dest_name = f"{UPLOAD_DIR}/{base}"

    if hasattr(storage, "path"):
        if storage.exists(dest_name):
            storage.delete(current_name)
        else:
            dest_dir = os.path.dirname(storage.path(dest_name))
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(storage.path(current_name), storage.path(dest_name))
    else:
        if not storage.exists(dest_name):
            with file_obj.file.open("rb") as handle:
                storage.save(dest_name, handle)
        storage.delete(current_name)

    file_obj.file.name = dest_name
    file_obj.save(update_fields=["file", "updated_at"])
    return dest_name


def purge_recycled_files(retention_days=None, max_files=None):
    """Delete recycled files, and the audit rows that still reference them.

    Recycle is a soft delete, so without a TTL the directory only ever grows.
    Anything older than SYLLABUS.RECYCLE_RETENTION_DAYS is dropped, capped at
    SYLLABUS.RECYCLE_MAX_FILES per run so one pass can never delete too much.
    Returns the number of files purged.
    """
    if retention_days is None:
        retention_days = int(settings.SYLLABUS["RECYCLE_RETENTION_DAYS"])
    if max_files is None:
        max_files = int(settings.SYLLABUS["RECYCLE_MAX_FILES"])

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    candidates = list(
        SyllabusFile.objects.filter(
            file__startswith=f"{RECYCLE_DIR}/", updated_at__lt=cutoff
        ).order_by("updated_at")[:max_files]
    )

    purged = 0
    for file_obj in candidates:
        try:
            if file_obj.syllabi.filter(status__in=ACTIVE_SYLLABUS_STATUSES).exists():
                continue
            # SyllabusFile is PROTECT'd by its syllabi; drop the audit rows first.
            file_obj.syllabi.all().delete()
            file_obj.file.delete(save=False)
            file_obj.delete()
            purged += 1
        except Exception:  # noqa: BLE001 - a bad entry must not stop the sweep
            logger.exception("Failed to purge recycled syllabus file %s", file_obj.pk)
    return purged
