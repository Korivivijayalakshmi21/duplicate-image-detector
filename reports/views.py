import csv
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import HttpResponse
from django.db.models import Sum
from images.models import Image, DuplicateGroup, DuplicateRelation


def fmt_bytes(b):
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.1f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"


class ReportView(LoginRequiredMixin, View):
    template_name = 'reports/report.html'

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

        user_image_ids = images.values_list('id', flat=True)
        group_ids = DuplicateRelation.objects.filter(
            image_id__in=user_image_ids
        ).values_list('duplicate_group_id', flat=True).distinct()
        groups = DuplicateGroup.objects.filter(id__in=group_ids).prefetch_related('relations__image').order_by('-created_at')

        group_data = []
        for group in groups:
            relations = group.relations.filter(image__user=user)
            imgs = [r.image for r in relations]
            sims = [r.similarity_score for r in relations if r.similarity_score is not None]
            avg_sim = round(sum(sims) / len(sims), 1) if sims else None
            group_data.append({
                'group': group,
                'images': imgs,
                'image_count': len(imgs),
                'avg_similarity': avg_sim,
                'total_size': fmt_bytes(sum(img.file_size for img in imgs)),
            })

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
            'groups': group_data,
            'all_images': images.order_by('status', 'filename'),
            'generated_at': timezone.now(),
        }
        return render(request, self.template_name, ctx)


class ExportCSVView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="duplidetect_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Filename', 'Status', 'File Size (bytes)', 'Width', 'Height',
                         'SHA-256 Hash', 'Perceptual Hash', 'Upload Date'])
        for img in Image.objects.filter(user=request.user).order_by('status', 'filename'):
            writer.writerow([
                img.filename,
                img.get_status_display(),
                img.file_size,
                img.width or '',
                img.height or '',
                img.sha256_hash,
                img.perceptual_hash or '',
                img.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        return response
