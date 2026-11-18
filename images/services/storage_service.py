"""
Storage Service - file validation and safe naming.
Abstracted so AWS S3 or other backends can be swapped in via settings.
"""
import os
import uuid
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def get_safe_filename(original_name: str) -> str:
    """Generate a unique, safe filename preserving the original extension."""
    ext = os.path.splitext(original_name)[1].lower()
    return uuid.uuid4().hex + ext


def validate_file_extension(filename: str) -> tuple:
    """
    Validate file extension against allowed types.
    Returns (is_valid: bool, error_message: str or None)
    """
    allowed = getattr(settings, 'ALLOWED_IMAGE_EXTENSIONS', ['jpg', 'jpeg', 'png', 'webp'])
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if ext not in allowed:
        exts_str = ', '.join(f'.{e.upper()}' for e in allowed)
        return False, f"Unsupported file type '.{ext}'. Please upload {exts_str}."
    return True, None


def validate_file_size(file_obj) -> tuple:
    """
    Validate that the file is within the allowed size limit and not empty.
    Returns (is_valid: bool, error_message: str or None)
    """
    max_mb = getattr(settings, 'MAX_IMAGE_SIZE_MB', 10)
    max_bytes = max_mb * 1024 * 1024

    file_obj.seek(0, 2)   # Seek to end
    size = file_obj.tell()
    file_obj.seek(0)       # Reset

    if size == 0:
        return False, "The uploaded file is empty."
    if size > max_bytes:
        return False, f"File too large ({size // (1024*1024)}MB). Maximum allowed size is {max_mb}MB."
    return True, None


def get_mime_type(filename: str) -> str:
    """Infer MIME type from file extension."""
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
    }
    return mime_map.get(ext, 'application/octet-stream')
