import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView
from .models import Image, DuplicateGroup, DuplicateRelation
from .services.detection_service import process_uploaded_image

logger = logging.getLogger(__name__)


class ImageUploadView(LoginRequiredMixin, View):
    template_name = 'images/upload.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        files = request.FILES.getlist('images')

        if not files:
            messages.error(request, 'Please select at least one image to upload.')
            return render(request, self.template_name)

        results = []
        success_count = 0
        duplicate_count = 0
        error_count = 0

        for file_obj in files:
            result = process_uploaded_image(file_obj, file_obj.name, request.user)
            results.append({**result, 'filename': file_obj.name})

            if result.get('success'):
                if result.get('status') in ('exact_duplicate', 'highly_similar', 'possible_duplicate'):
                    duplicate_count += 1
                else:
                    success_count += 1
            else:
                error_count += 1

        # Build user feedback
        total = success_count + duplicate_count
        if total > 0:
            if duplicate_count > 0 and success_count > 0:
                messages.warning(
                    request,
                    f'{total} image(s) processed: {success_count} unique, {duplicate_count} duplicate(s) detected.'
                )
            elif duplicate_count > 0:
                messages.warning(request, f'{duplicate_count} duplicate image(s) detected.')
            else:
                messages.success(request, f'{success_count} image(s) uploaded and analyzed successfully.')

        for result in results:
            if not result.get('success'):
                messages.error(request, f"{result.get('filename', 'File')}: {result.get('error', 'Upload failed.')}")

        return render(request, self.template_name, {'results': results})


class ImageLibraryView(LoginRequiredMixin, ListView):
    template_name = 'images/library.html'
    context_object_name = 'images'
    paginate_by = 20

    def get_queryset(self):
        qs = Image.objects.filter(user=self.request.user)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(filename__icontains=q)

        status = self.request.GET.get('status', '')
        if status:
            qs = qs.filter(status=status)

        sort = self.request.GET.get('sort', 'newest')
        sort_map = {
            'newest': '-uploaded_at',
            'oldest': 'uploaded_at',
            'name': 'filename',
            'size_desc': '-file_size',
            'size_asc': 'file_size',
        }
        return qs.order_by(sort_map.get(sort, '-uploaded_at'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = self.request.GET.get('q', '')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['sort'] = self.request.GET.get('sort', 'newest')
        ctx['status_choices'] = [
            ('', 'All Images'),
            ('unique', 'Unique'),
            ('exact_duplicate', 'Exact Duplicates'),
            ('highly_similar', 'Highly Similar'),
            ('possible_duplicate', 'Possible Duplicates'),
        ]
        ctx['sort_choices'] = [
            ('newest', 'Newest First'),
            ('oldest', 'Oldest First'),
            ('name', 'Filename A-Z'),
            ('size_desc', 'Largest First'),
            ('size_asc', 'Smallest First'),
        ]
        ctx['total_count'] = Image.objects.filter(user=self.request.user).count()
        return ctx


class ImageDetailView(LoginRequiredMixin, DetailView):
    model = Image
    template_name = 'images/detail.html'
    context_object_name = 'image'

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['relations'] = self.object.duplicate_relations.select_related('duplicate_group').all()
        return ctx


class ImageDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        image = get_object_or_404(Image, pk=pk, user=request.user)
        filename = image.filename
        try:
            if image.file and image.file.name:
                try:
                    image.file.delete(save=False)
                except Exception:
                    pass
            image.delete()
            messages.success(request, f'"{filename}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting image {pk}: {e}")
            messages.error(request, 'Failed to delete image. Please try again.')
        return redirect('images:library')


class ImageCompareView(LoginRequiredMixin, View):
    template_name = 'images/compare.html'

    def get(self, request):
        img_a_id = request.GET.get('a')
        img_b_id = request.GET.get('b')

        image_a = image_b = comparison = None

        if img_a_id and img_b_id:
            try:
                image_a = get_object_or_404(Image, pk=img_a_id, user=request.user)
                image_b = get_object_or_404(Image, pk=img_b_id, user=request.user)

                from images.services.hash_service import hamming_distance, similarity_percentage
                from images.services.similarity_service import classify_similarity

                if image_a.sha256_hash == image_b.sha256_hash:
                    dist, sim_pct, classification = 0, 100.0, 'exact_duplicate'
                elif image_a.perceptual_hash and image_b.perceptual_hash:
                    dist = hamming_distance(image_a.perceptual_hash, image_b.perceptual_hash)
                    sim_pct = similarity_percentage(dist)
                    classification = classify_similarity(dist)
                else:
                    dist, sim_pct, classification = None, None, 'unknown'

                comparison = {
                    'similarity': sim_pct,
                    'hamming_distance': dist,
                    'classification': classification,
                    'same_hash': image_a.sha256_hash == image_b.sha256_hash,
                }
            except Exception as e:
                logger.error(f"Compare error: {e}")
                messages.error(request, 'Could not compare these images.')

        user_images = Image.objects.filter(user=request.user).order_by('filename')
        return render(request, self.template_name, {
            'image_a': image_a,
            'image_b': image_b,
            'comparison': comparison,
            'user_images': user_images,
            'img_a_id': img_a_id,
            'img_b_id': img_b_id,
        })


class DuplicateGroupListView(LoginRequiredMixin, ListView):
    template_name = 'images/groups.html'
    context_object_name = 'groups'
    paginate_by = 10

    def get_queryset(self):
        user_image_ids = Image.objects.filter(user=self.request.user).values_list('id', flat=True)
        group_ids = DuplicateRelation.objects.filter(
            image_id__in=user_image_ids
        ).values_list('duplicate_group_id', flat=True).distinct()
        qs = DuplicateGroup.objects.filter(id__in=group_ids).prefetch_related('relations__image')
        gtype = self.request.GET.get('type', '')
        if gtype:
            qs = qs.filter(group_type=gtype)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['group_type_filter'] = self.request.GET.get('type', '')
        return ctx


class DuplicateGroupDetailView(LoginRequiredMixin, DetailView):
    model = DuplicateGroup
    template_name = 'images/group_detail.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        relations = self.object.relations.select_related('image').filter(
            image__user=self.request.user
        ).order_by('-similarity_score')
        ctx['relations'] = relations
        return ctx
