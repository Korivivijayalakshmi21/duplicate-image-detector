"""
Hash Service - SHA-256 and perceptual hashing for duplicate detection.
"""
import hashlib
import logging

import imagehash
from PIL import Image as PILImage

logger = logging.getLogger(__name__)


def calculate_sha256(file_obj) -> str:
    """Calculate SHA-256 hash of a file object. Deterministic regardless of filename."""
    sha256 = hashlib.sha256()
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(8192), b''):
        sha256.update(chunk)
    file_obj.seek(0)
    return sha256.hexdigest()


def calculate_perceptual_hash(file_obj) -> str:
    """
    Calculate perceptual hash (pHash) of an image.
    pHash is robust to resizing, minor color shifts, and compression.
    Returns hex string like 'f8c8b4e0c0a4b4e0' or None on failure.
    """
    try:
        file_obj.seek(0)
        img = PILImage.open(file_obj)
        img = img.convert('RGB')
        phash = imagehash.phash(img)
        file_obj.seek(0)
        return str(phash)
    except Exception as e:
        logger.error(f"Error calculating perceptual hash: {e}")
        return None


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two perceptual hash hex strings.
    Lower distance = more similar images.
    Distance 0 = identical perceptual content.
    """
    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except Exception as e:
        logger.error(f"Error calculating hamming distance: {e}")
        return 999


def similarity_percentage(hamming_dist: int, hash_bits: int = 64) -> float:
    """
    Convert Hamming distance to a human-readable similarity percentage.
    0 distance -> 100% similar
    64 distance -> 0% similar (for 64-bit hash)
    """
    max_dist = hash_bits
    similarity = max(0.0, (max_dist - hamming_dist) / max_dist * 100)
    return round(similarity, 1)


def get_image_info(file_obj) -> dict:
    """Extract image dimensions and format metadata."""
    try:
        file_obj.seek(0)
        img = PILImage.open(file_obj)
        info = {
            'width': img.width,
            'height': img.height,
            'format': img.format or 'unknown',
            'mode': img.mode,
        }
        file_obj.seek(0)
        return info
    except Exception as e:
        logger.error(f"Error getting image info: {e}")
        return {'width': None, 'height': None, 'format': 'unknown', 'mode': 'unknown'}


def validate_image(file_obj) -> tuple:
    """
    Validate that the file is a real, non-corrupted image.
    Returns (is_valid: bool, error_message: str or None)
    """
    try:
        file_obj.seek(0)
        img = PILImage.open(file_obj)
        img.verify()  # Verifies the image without fully decoding it
        file_obj.seek(0)
        return True, None
    except Exception as e:
        return False, f"Invalid or corrupted image file."
