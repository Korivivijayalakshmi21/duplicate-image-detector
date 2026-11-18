from django.contrib import admin
from .models import Image, DuplicateGroup, DuplicateRelation


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['filename', 'user', 'status', 'file_size', 'width', 'height', 'uploaded_at']
    list_filter = ['status', 'mime_type', 'uploaded_at']
    search_fields = ['filename', 'sha256_hash', 'user__username']
    readonly_fields = ['sha256_hash', 'perceptual_hash', 'uploaded_at']
    ordering = ['-uploaded_at']


@admin.register(DuplicateGroup)
class DuplicateGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'group_type', 'image_count', 'avg_similarity', 'created_at']
    list_filter = ['group_type']


@admin.register(DuplicateRelation)
class DuplicateRelationAdmin(admin.ModelAdmin):
    list_display = ['image', 'duplicate_group', 'similarity_score', 'detection_type', 'hamming_distance']
    list_filter = ['detection_type']
