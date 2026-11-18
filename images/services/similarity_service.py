"""
Similarity Service - classify images based on perceptual hash distances.
"""
import logging
from django.conf import settings
from .hash_service import hamming_distance, similarity_percentage

logger = logging.getLogger(__name__)

# Thresholds (configurable via settings)
EXACT_THRESHOLD = getattr(settings, 'EXACT_DUPLICATE_THRESHOLD', 0)
HIGHLY_SIMILAR_THRESHOLD = getattr(settings, 'HIGHLY_SIMILAR_THRESHOLD', 5)
POSSIBLE_DUPLICATE_THRESHOLD = getattr(settings, 'POSSIBLE_DUPLICATE_THRESHOLD', 10)


def classify_similarity(hamming_dist: int) -> str:
    """
    Classify two images based on their perceptual Hamming distance.

    Returns one of:
        'exact_duplicate'   - distance <= 0  (perceptually identical)
        'highly_similar'    - distance 1-5   (resized/compressed versions)
        'possible_duplicate'- distance 6-10  (possible near-duplicate)
        'unique'            - distance > 10  (different images)
    """
    if hamming_dist <= EXACT_THRESHOLD:
        return 'exact_duplicate'
    elif hamming_dist <= HIGHLY_SIMILAR_THRESHOLD:
        return 'highly_similar'
    elif hamming_dist <= POSSIBLE_DUPLICATE_THRESHOLD:
        return 'possible_duplicate'
    else:
        return 'unique'


def get_status_label(status: str) -> str:
    """Human-readable label for a status code."""
    labels = {
        'exact_duplicate': 'Exact Duplicate',
        'highly_similar': 'Highly Similar',
        'possible_duplicate': 'Possible Duplicate',
        'unique': 'Unique',
        'pending': 'Pending',
    }
    return labels.get(status, status.replace('_', ' ').title())


def find_similar_images(new_hash: str, existing_images, exclude_id=None) -> list:
    """
    Compare new_hash against all existing images using perceptual hashing.

    Returns a sorted list of (image, hamming_dist, similarity_pct, classification)
    tuples for non-unique matches, ordered by ascending distance (best match first).
    """
    results = []
    for img in existing_images:
        if exclude_id and img.id == exclude_id:
            continue
        if not img.perceptual_hash:
            continue
        dist = hamming_distance(new_hash, img.perceptual_hash)
        sim_pct = similarity_percentage(dist)
        classification = classify_similarity(dist)
        if classification != 'unique':
            results.append((img, dist, sim_pct, classification))
    # Best match (lowest distance) first
    results.sort(key=lambda x: x[1])
    return results
