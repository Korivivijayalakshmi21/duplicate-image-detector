"""
Detection Service - core duplicate detection engine.

Flow:
1. Validate file (extension, size, image integrity)
2. Compute SHA-256 hash  -> check for EXACT duplicates
3. Compute perceptual hash (pHash) -> check for VISUAL duplicates
4. Classify and persist to database
5. Return structured result dict
"""
import logging
from django.db import transaction
from django.contrib.auth.models import User

from images.models import Image, DuplicateGroup, DuplicateRelation
from .hash_service import (
    calculate_sha256,
    calculate_perceptual_hash,
    get_image_info,
    validate_image,
    hamming_distance,
    similarity_percentage,
)
from .similarity_service import classify_similarity, find_similar_images
from .storage_service import (
    validate_file_extension,
    validate_file_size,
    get_safe_filename,
    get_mime_type,
)

logger = logging.getLogger(__name__)


def process_uploaded_image(file_obj, original_filename: str, user: User) -> dict:
    """
    Main entry point for image processing.

    Returns:
        {
            'success': bool,
            'status': str,          # 'unique' | 'exact_duplicate' | 'highly_similar' | 'possible_duplicate'
            'message': str,
            'image_id': int,
            'detection_info': dict,
            'error': str,           # only on failure
        }
    """
    # --- Step 1: Validate extension ---
    ext_valid, ext_err = validate_file_extension(original_filename)
    if not ext_valid:
        return {'success': False, 'error': ext_err}

    # --- Step 2: Validate file size ---
    size_valid, size_err = validate_file_size(file_obj)
    if not size_valid:
        return {'success': False, 'error': size_err}

    # --- Step 3: Validate image integrity ---
    img_valid, img_err = validate_image(file_obj)
    if not img_valid:
        return {'success': False, 'error': img_err or 'Invalid or corrupted image file.'}

    try:
        # --- Step 4: Compute hashes ---
        sha256 = calculate_sha256(file_obj)
        phash = calculate_perceptual_hash(file_obj)
        img_info = get_image_info(file_obj)

        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(0)

        mime_type = get_mime_type(original_filename)

        with transaction.atomic():

            # --- Step 5: Exact duplicate check (SHA-256) ---
            existing_exact = Image.objects.filter(
                sha256_hash=sha256, user=user
            ).first()

            if existing_exact:
                image_obj = _save_image(
                    file_obj, original_filename, user, sha256, phash,
                    img_info, file_size, mime_type, 'exact_duplicate'
                )
                group = _get_or_create_exact_group(existing_exact)
                _add_to_group(image_obj, group, 100.0, 'sha256', 0)
                _add_to_group(existing_exact, group, 100.0, 'sha256', 0)
                return {
                    'success': True,
                    'status': 'exact_duplicate',
                    'message': f'Exact duplicate of "{existing_exact.filename}" detected (SHA-256 match).',
                    'image_id': image_obj.id,
                    'detection_info': {
                        'duplicate_of': existing_exact.filename,
                        'duplicate_of_id': existing_exact.id,
                        'similarity': 100.0,
                        'hamming_distance': 0,
                        'method': 'SHA-256 Hash Match',
                    }
                }

            # --- Step 6: Visual duplicate check (pHash) ---
            if phash:
                user_images = Image.objects.filter(
                    user=user, perceptual_hash__isnull=False
                ).exclude(sha256_hash=sha256)

                similar_matches = find_similar_images(phash, user_images)

                if similar_matches:
                    best_match_img, dist, sim_pct, classification = similar_matches[0]
                    image_obj = _save_image(
                        file_obj, original_filename, user, sha256, phash,
                        img_info, file_size, mime_type, classification
                    )
                    group = _get_or_create_similar_group(best_match_img)
                    _add_to_group(image_obj, group, sim_pct, 'perceptual', dist)
                    _add_to_group(best_match_img, group, sim_pct, 'perceptual', dist)

                    label = 'highly similar' if classification == 'highly_similar' else 'possibly duplicate'
                    return {
                        'success': True,
                        'status': classification,
                        'message': f'Image is {label} to "{best_match_img.filename}" ({sim_pct}% similarity, Hamming distance: {dist}).',
                        'image_id': image_obj.id,
                        'detection_info': {
                            'duplicate_of': best_match_img.filename,
                            'duplicate_of_id': best_match_img.id,
                            'similarity': sim_pct,
                            'hamming_distance': dist,
                            'method': 'Perceptual Hash (pHash)',
                        }
                    }

            # --- Step 7: Unique image ---
            image_obj = _save_image(
                file_obj, original_filename, user, sha256, phash,
                img_info, file_size, mime_type, 'unique'
            )
            return {
                'success': True,
                'status': 'unique',
                'message': 'Image uploaded successfully. No duplicates found.',
                'image_id': image_obj.id,
                'detection_info': {
                    'duplicate_of': None,
                    'similarity': None,
                    'hamming_distance': None,
                    'method': None,
                }
            }

    except Exception as e:
        logger.error(f"Error processing image {original_filename}: {e}", exc_info=True)
        return {'success': False, 'error': 'Image processing failed. Please try again.'}


def _save_image(file_obj, original_filename, user, sha256, phash,
                img_info, file_size, mime_type, status):
    """Persist the image record to the database."""
    file_obj.seek(0)
    image_obj = Image(
        user=user,
        filename=original_filename,
        file_size=file_size,
        mime_type=mime_type,
        width=img_info.get('width'),
        height=img_info.get('height'),
        sha256_hash=sha256,
        perceptual_hash=phash,
        status=status,
    )
    image_obj.file.save(original_filename, file_obj, save=True)
    return image_obj


def _get_or_create_exact_group(existing_image):
    """Find or create an exact-duplicate group for the given anchor image."""
    relation = DuplicateRelation.objects.filter(
        image=existing_image,
        duplicate_group__group_type='exact'
    ).first()
    if relation:
        return relation.duplicate_group
    return DuplicateGroup.objects.create(group_type='exact')


def _get_or_create_similar_group(existing_image):
    """Find or create a similarity group for the given anchor image."""
    relation = DuplicateRelation.objects.filter(
        image=existing_image,
        duplicate_group__group_type='similar'
    ).first()
    if relation:
        return relation.duplicate_group
    return DuplicateGroup.objects.create(group_type='similar')


def _add_to_group(image_obj, group, similarity_score, detection_type, hamming_dist):
    """Add an image to a duplicate group (idempotent)."""
    DuplicateRelation.objects.get_or_create(
        image=image_obj,
        duplicate_group=group,
        defaults={
            'similarity_score': similarity_score,
            'detection_type': detection_type,
            'hamming_distance': hamming_dist,
        }
    )
