from django.db import models
from django.contrib.auth.models import User
import os


STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('unique', 'Unique'),
    ('exact_duplicate', 'Exact Duplicate'),
    ('highly_similar', 'Highly Similar'),
    ('possible_duplicate', 'Possible Duplicate'),
]

DETECTION_TYPE_CHOICES = [
    ('sha256', 'SHA-256 Hash Match'),
    ('perceptual', 'Perceptual Hash Match'),
]

GROUP_TYPE_CHOICES = [
    ('exact', 'Exact Duplicates'),
    ('similar', 'Similar Images'),
]


class Image(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='images')
    filename = models.CharField(max_length=255)
    file = models.ImageField(upload_to='uploads/%Y/%m/%d/')
    file_size = models.PositiveBigIntegerField(help_text='File size in bytes')
    mime_type = models.CharField(max_length=50)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    sha256_hash = models.CharField(max_length=64, db_index=True)
    perceptual_hash = models.CharField(max_length=64, db_index=True, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['sha256_hash', 'user']),
        ]

    def __str__(self):
        return self.filename

    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def file_size_display(self):
        b = self.file_size
        if b >= 1024 ** 3:
            return f"{b / 1024 ** 3:.1f} GB"
        if b >= 1024 ** 2:
            return f"{b / 1024 ** 2:.1f} MB"
        if b >= 1024:
            return f"{b / 1024:.1f} KB"
        return f"{b} B"

    @property
    def dimensions(self):
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Unknown"

    @property
    def status_badge_class(self):
        mapping = {
            'unique': 'success',
            'exact_duplicate': 'danger',
            'highly_similar': 'warning',
            'possible_duplicate': 'info',
            'pending': 'secondary',
        }
        return mapping.get(self.status, 'secondary')

    @property
    def status_icon(self):
        mapping = {
            'unique': 'fa-check-circle',
            'exact_duplicate': 'fa-clone',
            'highly_similar': 'fa-equals',
            'possible_duplicate': 'fa-question-circle',
            'pending': 'fa-clock',
        }
        return mapping.get(self.status, 'fa-circle')


class DuplicateGroup(models.Model):
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Group #{self.pk} ({self.get_group_type_display()})"

    @property
    def image_count(self):
        return self.relations.count()

    @property
    def avg_similarity(self):
        relations = self.relations.filter(similarity_score__isnull=False)
        scores = list(relations.values_list('similarity_score', flat=True))
        if scores:
            return round(sum(scores) / len(scores), 1)
        return 0


class DuplicateRelation(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name='duplicate_relations')
    duplicate_group = models.ForeignKey(DuplicateGroup, on_delete=models.CASCADE, related_name='relations')
    similarity_score = models.FloatField(null=True, blank=True, help_text='Similarity percentage 0-100')
    detection_type = models.CharField(max_length=20, choices=DETECTION_TYPE_CHOICES)
    hamming_distance = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = [['image', 'duplicate_group']]

    def __str__(self):
        return f"{self.image.filename} in {self.duplicate_group}"
