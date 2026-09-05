"""Filesystem helpers for syllabus files: recycle (soft-delete) storage.

Files live in MEDIA_ROOT/syllabi/<sha256>.<ext> and are shared by
Syllabus rows via sha256 dedup. When the last referencing syllabus is
rejected or deleted the file moves to MEDIA_ROOT/recycle/ instead of
being destroyed, so an admin can audit and restore it.
"""

from __future__ import unicode_literals

import os
import shutil
from datetime import datetime, timezone

from django.core.files.storage import default_storage

RECYCLE_DIR = "recycle"


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
