"""TC: Service layer unit tests."""
import io
import hashlib
from PIL import Image as PILImage
from django.test import TestCase
from images.services.hash_service import (
    calculate_sha256,
    calculate_perceptual_hash,
    hamming_distance,
    similarity_percentage,
    validate_image,
    get_image_info,
)
from images.services.similarity_service import classify_similarity
from images.services.storage_service import validate_file_extension, validate_file_size


def make_test_image(w=100, h=100, color=(100, 149, 237), fmt='JPEG'):
    img = PILImage.new('RGB', (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf


class SHA256Test(TestCase):
    def test_deterministic(self):
        buf = make_test_image()
        data = buf.read()
        expected = hashlib.sha256(data).hexdigest()
        h = calculate_sha256(io.BytesIO(data))
        self.assertEqual(h, expected)

    def test_different_images_different_hash(self):
        h1 = calculate_sha256(make_test_image(color=(100, 100, 100)))
        h2 = calculate_sha256(make_test_image(color=(200, 200, 200)))
        self.assertNotEqual(h1, h2)

    def test_hash_length_is_64(self):
        h = calculate_sha256(make_test_image())
        self.assertEqual(len(h), 64)


class PerceptualHashTest(TestCase):
    def test_returns_string(self):
        phash = calculate_perceptual_hash(make_test_image())
        self.assertIsInstance(phash, str)
        self.assertGreater(len(phash), 0)

    def test_same_image_same_hash(self):
        data = make_test_image().read()
        h1 = calculate_perceptual_hash(io.BytesIO(data))
        h2 = calculate_perceptual_hash(io.BytesIO(data))
        self.assertEqual(h1, h2)

    def test_similar_images_low_distance(self):
        # Same color, different sizes -> should be very similar
        h1 = calculate_perceptual_hash(make_test_image(w=200, h=200, color=(70, 130, 180)))
        h2 = calculate_perceptual_hash(make_test_image(w=100, h=100, color=(70, 130, 180)))
        dist = hamming_distance(h1, h2)
        self.assertLessEqual(dist, 15, "Resized same-color image should have low hamming distance")

    def test_hamming_distance_same_hash_is_zero(self):
        data = make_test_image().read()
        h = calculate_perceptual_hash(io.BytesIO(data))
        self.assertEqual(hamming_distance(h, h), 0)


class SimilarityPercentageTest(TestCase):
    def test_distance_zero_is_100_pct(self):
        self.assertEqual(similarity_percentage(0), 100.0)

    def test_distance_64_is_0_pct(self):
        self.assertEqual(similarity_percentage(64), 0.0)

    def test_distance_32_is_50_pct(self):
        self.assertEqual(similarity_percentage(32), 50.0)


class ClassifySimilarityTest(TestCase):
    def test_exact(self):
        self.assertEqual(classify_similarity(0), 'exact_duplicate')

    def test_highly_similar(self):
        self.assertEqual(classify_similarity(3), 'highly_similar')

    def test_possible_duplicate(self):
        self.assertEqual(classify_similarity(8), 'possible_duplicate')

    def test_unique(self):
        self.assertEqual(classify_similarity(20), 'unique')


class ValidateImageTest(TestCase):
    def test_valid_image(self):
        buf = make_test_image()
        is_valid, err = validate_image(buf)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_invalid_image(self):
        buf = io.BytesIO(b'this is not an image file at all!!')
        is_valid, err = validate_image(buf)
        self.assertFalse(is_valid)
        self.assertIsNotNone(err)


class GetImageInfoTest(TestCase):
    def test_dimensions(self):
        buf = make_test_image(w=200, h=150)
        info = get_image_info(buf)
        self.assertEqual(info['width'], 200)
        self.assertEqual(info['height'], 150)


class FileExtensionTest(TestCase):
    def test_jpg_valid(self):
        ok, err = validate_file_extension('photo.jpg')
        self.assertTrue(ok)

    def test_jpeg_valid(self):
        ok, err = validate_file_extension('photo.JPEG')
        self.assertTrue(ok)

    def test_png_valid(self):
        ok, err = validate_file_extension('image.PNG')
        self.assertTrue(ok)

    def test_webp_valid(self):
        ok, err = validate_file_extension('anim.webp')
        self.assertTrue(ok)

    def test_pdf_invalid(self):
        ok, err = validate_file_extension('doc.pdf')
        self.assertFalse(ok)
        self.assertIn('Unsupported', err)

    def test_exe_invalid(self):
        ok, err = validate_file_extension('virus.exe')
        self.assertFalse(ok)


class FileSizeTest(TestCase):
    def test_too_large(self):
        big = io.BytesIO(b'x' * (11 * 1024 * 1024))
        ok, err = validate_file_size(big)
        self.assertFalse(ok)
        self.assertIn('large', err.lower())

    def test_ok_size(self):
        small = io.BytesIO(b'x' * 1000)
        ok, err = validate_file_size(small)
        self.assertTrue(ok)

    def test_empty_file(self):
        empty = io.BytesIO(b'')
        ok, err = validate_file_size(empty)
        self.assertFalse(ok)
        self.assertIn('empty', err.lower())
