import json
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from images.models import Image, DuplicateGroup, DuplicateRelation


def fmt_bytes(b):
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.1f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"


class DashboardView(LoginRequiredMixin, View):
    template_name = 'dashboard/home.html'

    def get(self, request):
        user = request.user
        images = Image.objects.filter(user=user)

        total_images = images.count()
        unique_images = images.filter(status='unique').count()
        exact_duplicates = images.filter(status='exact_duplicate').count()
        highly_similar = images.filter(status='highly_similar').count()
        possible_duplicates = images.filter(status='possible_duplicate').count()
        all_duplicates = exact_duplicates + highly_similar + possible_duplicates
        duplicate_pct = round(all_duplicates / total_images * 100, 1) if total_images > 0 else 0.0

        total_storage = images.aggregate(total=Sum('file_size'))['total'] or 0
        duplicate_storage = images.filter(
            status__in=['exact_duplicate', 'highly_similar', 'possible_duplicate']
        ).aggregate(total=Sum('file_size'))['total'] or 0

        # Duplicate groups
        user_image_ids = images.values_list('id', flat=True)
        group_ids = set(DuplicateRelation.objects.filter(
            image_id__in=user_image_ids
        ).values_list('duplicate_group_id', flat=True))
        duplicate_groups_count = len(group_ids)

        # Upload trend (last 14 days)
        fourteen_days_ago = timezone.now() - timedelta(days=14)
        upload_trend = (
            images.filter(uploaded_at__gte=fourteen_days_ago)
            .annotate(date=TruncDate('uploaded_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        trend_labels = [item['date'].strftime('%b %d') for item in upload_trend]
        trend_data = [item['count'] for item in upload_trend]

        # Recent duplicates
        recent_dupes = images.filter(
            status__in=['exact_duplicate', 'highly_similar', 'possible_duplicate']
        ).order_by('-uploaded_at')[:5]

        ctx = {
            'total_images': total_images,
            'unique_images': unique_images,
            'exact_duplicates': exact_duplicates,
            'highly_similar': highly_similar,
            'possible_duplicates': possible_duplicates,
            'all_duplicates': all_duplicates,
            'duplicate_pct': duplicate_pct,
            'total_storage': fmt_bytes(total_storage),
            'duplicate_storage': fmt_bytes(duplicate_storage),
            'potential_savings': fmt_bytes(duplicate_storage),
            'duplicate_groups_count': duplicate_groups_count,
            'trend_labels_json': json.dumps(trend_labels),
            'trend_data_json': json.dumps(trend_data),
            'status_data_json': json.dumps({
                'unique': unique_images,
                'exact_duplicate': exact_duplicates,
                'highly_similar': highly_similar,
                'possible_duplicate': possible_duplicates,
            }),
            'recent_dupes': recent_dupes,
        }
        return render(request, self.template_name, ctx)
