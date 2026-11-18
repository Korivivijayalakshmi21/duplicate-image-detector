"""TC: Model integrity tests."""
from django.test import TestCase
from django.contrib.auth.models import User
from images.models import Image, DuplicateGroup, DuplicateRelation


class ImageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('modeluser', password='pass123')

    def test_image_str_returns_filename(self):
        img = Image(user=self.user, filename='test.jpg',
                    sha256_hash='abc123', file_size=1000, mime_type='image/jpeg')
        self.assertEqual(str(img), 'test.jpg')

    def test_file_size_mb_property(self):
        img = Image(user=self.user, filename='test.jpg',
                    sha256_hash='abc', file_size=2097152, mime_type='image/jpeg')
        self.assertAlmostEqual(img.file_size_mb, 2.0)

    def test_dimensions_with_values(self):
        img = Image(user=self.user, filename='t.jpg', sha256_hash='x',
                    file_size=100, mime_type='image/jpeg', width=1920, height=1080)
        self.assertEqual(img.dimensions, '1920x1080')

    def test_dimensions_without_values(self):
        img = Image(user=self.user, filename='t.jpg', sha256_hash='x',
                    file_size=100, mime_type='image/jpeg')
        self.assertEqual(img.dimensions, 'Unknown')

    def test_status_badge_class_unique(self):
        img = Image(user=self.user, filename='t.jpg', sha256_hash='x',
                    file_size=100, mime_type='image/jpeg', status='unique')
        self.assertEqual(img.status_badge_class, 'success')

    def test_status_badge_class_exact(self):
        img = Image(user=self.user, filename='t.jpg', sha256_hash='x',
                    file_size=100, mime_type='image/jpeg', status='exact_duplicate')
        self.assertEqual(img.status_badge_class, 'danger')

    def test_duplicate_group_str(self):
        group = DuplicateGroup.objects.create(group_type='exact')
        self.assertIn('exact', str(group).lower())
        self.assertIn(str(group.pk), str(group))

    def test_duplicate_relation_unique_together(self):
        from django.db import IntegrityError
        img = Image.objects.create(
            user=self.user, filename='t.jpg', sha256_hash='abc',
            file_size=100, mime_type='image/jpeg', status='unique'
        )
        group = DuplicateGroup.objects.create(group_type='exact')
        DuplicateRelation.objects.create(
            image=img, duplicate_group=group,
            similarity_score=100.0, detection_type='sha256', hamming_distance=0
        )
        with self.assertRaises(Exception):
            DuplicateRelation.objects.create(
                image=img, duplicate_group=group,
                similarity_score=100.0, detection_type='sha256', hamming_distance=0
            )
