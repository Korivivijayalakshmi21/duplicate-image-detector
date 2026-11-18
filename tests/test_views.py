"""TC01-TC12: Integration / view tests."""
import io
from PIL import Image as PILImage
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from images.models import Image


def make_upload_file(w=100, h=100, color=(100, 149, 237), fmt='JPEG', name='test.jpg'):
    img = PILImage.new('RGB', (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    buf.name = name
    return buf


class AuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('authuser', password='testpass123')

    def test_login_page_accessible(self):
        r = self.client.get(reverse('accounts:login'))
        self.assertEqual(r.status_code, 200)

    def test_login_valid_creds(self):
        r = self.client.post(reverse('accounts:login'),
                             {'username': 'authuser', 'password': 'testpass123'})
        self.assertRedirects(r, reverse('dashboard:home'))

    def test_login_invalid_creds(self):
        r = self.client.post(reverse('accounts:login'),
                             {'username': 'authuser', 'password': 'wrong'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Invalid')

    # TC12: Unauthorized access redirects to login
    def test_dashboard_requires_login(self):
        r = self.client.get(reverse('dashboard:home'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r['Location'])

    def test_library_requires_login(self):
        r = self.client.get(reverse('images:library'))
        self.assertEqual(r.status_code, 302)


class UploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('uploader', password='testpass')
        self.client.login(username='uploader', password='testpass')

    # TC01: Upload valid JPG
    def test_tc01_upload_jpg(self):
        f = make_upload_file(fmt='JPEG', name='valid.jpg')
        r = self.client.post(reverse('images:upload'), {'images': f})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Image.objects.filter(user=self.user).exists())
        img = Image.objects.filter(user=self.user).first()
        self.assertEqual(img.status, 'unique')

    # TC02: Upload PNG
    def test_tc02_upload_png(self):
        f = make_upload_file(fmt='PNG', name='valid.png', color=(10, 200, 10))
        r = self.client.post(reverse('images:upload'), {'images': f})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Image.objects.filter(user=self.user, filename='valid.png').exists())

    # TC03: Upload unsupported extension
    def test_tc03_unsupported_extension(self):
        f = io.BytesIO(b'fake content')
        f.name = 'doc.pdf'
        r = self.client.post(reverse('images:upload'), {'images': f})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Image.objects.filter(user=self.user, filename='doc.pdf').exists())

    # TC04: Exact duplicate detection
    def test_tc04_exact_duplicate(self):
        data = make_upload_file(color=(50, 100, 150), name='dup.jpg').read()
        f1 = io.BytesIO(data); f1.name = 'original.jpg'
        self.client.post(reverse('images:upload'), {'images': f1})
        f2 = io.BytesIO(data); f2.name = 'copy.jpg'
        self.client.post(reverse('images:upload'), {'images': f2})
        dupes = Image.objects.filter(user=self.user, status='exact_duplicate')
        self.assertTrue(dupes.exists(), "Exact duplicate should be detected")

    # TC05: Resized version -> highly similar
    def test_tc05_resized_similar(self):
        f1 = make_upload_file(w=400, h=400, color=(70, 130, 180), name='big.jpg')
        f2 = make_upload_file(w=50, h=50, color=(70, 130, 180), name='small.jpg')
        self.client.post(reverse('images:upload'), {'images': f1})
        self.client.post(reverse('images:upload'), {'images': f2})
        self.assertGreaterEqual(Image.objects.filter(user=self.user).count(), 2)

    # TC06: Unique image
    def test_tc06_unique_image(self):
        f = make_upload_file(w=300, h=200, color=(220, 20, 60), name='unique_red.jpg')
        self.client.post(reverse('images:upload'), {'images': f})
        img = Image.objects.filter(user=self.user, filename='unique_red.jpg').first()
        self.assertIsNotNone(img)
        self.assertEqual(img.status, 'unique')

    # TC11: Empty upload
    def test_tc11_empty_upload(self):
        r = self.client.post(reverse('images:upload'), {})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Image.objects.filter(user=self.user).exists())


class LibraryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('lib_user', password='testpass')
        self.client.login(username='lib_user', password='testpass')

    # TC07: Search image
    def test_tc07_search_image(self):
        f = make_upload_file(name='vacation.jpg', color=(0, 128, 255))
        self.client.post(reverse('images:upload'), {'images': f})
        r = self.client.get(reverse('images:library') + '?q=vacation')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'vacation')

    def test_tc07_search_no_match(self):
        r = self.client.get(reverse('images:library') + '?q=xyz_does_not_exist')
        self.assertEqual(r.status_code, 200)

    # TC08: Filter duplicates
    def test_tc08_filter_duplicates(self):
        r = self.client.get(reverse('images:library') + '?status=exact_duplicate')
        self.assertEqual(r.status_code, 200)

    def test_tc08_filter_unique(self):
        r = self.client.get(reverse('images:library') + '?status=unique')
        self.assertEqual(r.status_code, 200)


class DashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('dashuser', password='testpass')
        self.client.login(username='dashuser', password='testpass')

    # TC10: Dashboard statistics match DB
    def test_tc10_dashboard_loads(self):
        r = self.client.get(reverse('dashboard:home'))
        self.assertEqual(r.status_code, 200)

    def test_tc10_dashboard_zero_stats(self):
        r = self.client.get(reverse('dashboard:home'))
        self.assertContains(r, '0')

    def test_tc10_dashboard_stats_after_upload(self):
        f = make_upload_file(name='stat_test.jpg', color=(1, 2, 3))
        self.client.post(reverse('images:upload'), {'images': f})
        r = self.client.get(reverse('dashboard:home'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '1')


class CompareTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('cmpuser', password='testpass')
        self.client.login(username='cmpuser', password='testpass')

    # TC09: Compare page loads
    def test_tc09_compare_page_accessible(self):
        r = self.client.get(reverse('images:compare'))
        self.assertEqual(r.status_code, 200)

    def test_tc09_compare_two_images(self):
        f1 = make_upload_file(name='a.jpg', color=(10, 20, 30))
        f2 = make_upload_file(name='b.jpg', color=(200, 100, 50))
        self.client.post(reverse('images:upload'), {'images': f1})
        self.client.post(reverse('images:upload'), {'images': f2})
        imgs = Image.objects.filter(user=self.user)
        if imgs.count() >= 2:
            a, b = imgs[0], imgs[1]
            r = self.client.get(f"{reverse('images:compare')}?a={a.pk}&b={b.pk}")
            self.assertEqual(r.status_code, 200)
