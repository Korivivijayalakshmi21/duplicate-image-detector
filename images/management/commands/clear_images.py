"""
Management command: clear_images
Deletes all images for a given user (useful for testing resets).

Usage:
    python manage.py clear_images
    python manage.py clear_images --username demo
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Delete all images for a user (for testing reset)'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo', help='Username whose images to clear')

    def handle(self, *args, **options):
        from images.models import Image
        try:
            user = User.objects.get(username=options['username'])
            count = Image.objects.filter(user=user).count()
            Image.objects.filter(user=user).delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {count} images for user "{user.username}".'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{options["username"]}" not found.'))
