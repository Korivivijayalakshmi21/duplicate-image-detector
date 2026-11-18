"""
Management command: load_sample_data
Creates synthetic sample images using Pillow to demonstrate all detection types.
No external image files required.

Usage:
    python manage.py load_sample_data
    python manage.py load_sample_data --username demo
    python manage.py load_sample_data --clear
"""
import io
from PIL import Image as PILImage, ImageDraw
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from images.services.detection_service import process_uploaded_image


class Command(BaseCommand):
    help = 'Load sample images for demonstration of duplicate detection'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo', help='Username to load sample data for')
        parser.add_argument('--password', default='demo1234', help='Password for new demo user')
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete existing images for this user before loading samples'
        )

    def handle(self, *args, **options):
        from images.models import Image

        username = options['username']
        password = options['password']

        # --- Get or create user ---
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com', 'first_name': 'Demo', 'last_name': 'User'}
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {username} / {password}'))
        else:
            self.stdout.write(f'Using existing user: {username}')

        # --- Optionally clear ---
        if options['clear']:
            count = Image.objects.filter(user=user).count()
            Image.objects.filter(user=user).delete()
            self.stdout.write(f'Cleared {count} existing images.')

        self.stdout.write('\nLoading sample images...\n')

        def make_image(w, h, color, text='', fmt='JPEG', noise_seed=None):
            """Generate a synthetic image with optional noise pattern to vary pixel content."""
            import random
            img = PILImage.new('RGB', (w, h), color=color)
            draw = ImageDraw.Draw(img)
            # Draw geometric pattern to make image content richer for pHash
            rng = random.Random(noise_seed if noise_seed is not None else 0)
            for _ in range(12):
                x1 = rng.randint(0, w - 1)
                y1 = rng.randint(0, h - 1)
                x2 = rng.randint(x1, min(x1 + w // 3, w - 1))
                y2 = rng.randint(y1, min(y1 + h // 3, h - 1))
                r = rng.randint(50, 255)
                g = rng.randint(50, 255)
                b = rng.randint(50, 255)
                draw.rectangle([x1, y1, x2, y2], fill=(r, g, b))
            if text:
                draw.text((w // 10, h // 2 - 15), text, fill=(255, 255, 255))
            buf = io.BytesIO()
            img.save(buf, format=fmt, quality=85)
            buf.seek(0)
            return buf

        def make_image_copy(source_buf):
            """Return an exact byte-for-byte copy of the source buffer."""
            source_buf.seek(0)
            data = source_buf.read()
            source_buf.seek(0)
            copy = io.BytesIO(data)
            return copy

        # --- Generate base images first so copies share exact bytes ---
        base_landscape = make_image(800, 600, (70, 130, 180), 'Original Landscape', noise_seed=42)
        base_landscape.seek(0); landscape_data = base_landscape.read(); base_landscape.seek(0)

        base_abstract = make_image(512, 512, (255, 165, 0), 'Abstract Art', 'PNG', noise_seed=99)
        base_abstract.seek(0); abstract_data = base_abstract.read(); base_abstract.seek(0)

        # Samples: (filename, description, generator_lambda)
        samples = [
            # Group A: Exact duplicates (SHA-256 match – same bytes)
            ('landscape_original.jpg',
             'Original landscape (800x600)',
             lambda: io.BytesIO(landscape_data)),
            ('landscape_exact_copy.jpg',
             'Exact copy – identical bytes, different name',
             lambda: io.BytesIO(landscape_data)),

            # Group B: Resized versions – same visual content, low pHash distance
            ('landscape_resized_400.jpg',
             'Resized 400x300 – visually similar',
             lambda: make_image(400, 300, (70, 130, 180), 'Original Landscape', noise_seed=42)),
            ('landscape_resized_200.jpg',
             'Resized 200x150 – visually similar',
             lambda: make_image(200, 150, (70, 130, 180), 'Original Landscape', noise_seed=42)),

            # Group C: Slight brightness shift – highly similar
            ('landscape_brightened.jpg',
             'Brightness-adjusted (+20 each channel)',
             lambda: make_image(800, 600, (90, 150, 200), 'Original Landscape', noise_seed=42)),

            # Group D: Abstract art exact copy
            ('abstract_orange.png',
             'Abstract orange art',
             lambda: io.BytesIO(abstract_data)),
            ('abstract_orange_copy.png',
             'Exact copy of abstract art',
             lambda: io.BytesIO(abstract_data)),

            # Unique images (completely different content)
            ('portrait_red.jpg',
             'Red portrait – unique',
             lambda: make_image(600, 800, (139, 0, 0), 'Red Portrait', noise_seed=7)),
            ('beach_cyan.jpg',
             'Cyan beach scene – unique',
             lambda: make_image(1024, 768, (0, 191, 255), 'Beach Scene', noise_seed=13)),
            ('forest_green.jpg',
             'Green forest – unique',
             lambda: make_image(900, 600, (34, 139, 34), 'Forest Scene', noise_seed=21)),
        ]

        success = 0
        for filename, desc, gen_fn in samples:
            buf = gen_fn()
            buf.name = filename
            result = process_uploaded_image(buf, filename, user)
            status = result.get('status', '?')
            if result.get('success'):
                icon = '✓'
                style = self.style.SUCCESS
                success += 1
            else:
                icon = '✗'
                style = self.style.WARNING
                status = result.get('error', 'error')
            self.stdout.write(style(f'  {icon} {filename:<35} -> {status}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'{success}/{len(samples)} sample images loaded successfully.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Login credentials: {username} / {password}'
        ))
        self.stdout.write('Start the server: python manage.py runserver')
