import django
from django.conf import settings


def pytest_configure(config):
    if not settings.configured:
        settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                'images',
                'dashboard',
                'reports',
                'accounts',
            ],
            ROOT_URLCONF='config.urls',
            TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': ['templates'],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ],
                },
            }],
            MEDIA_ROOT='/tmp/test_media/',
            MEDIA_URL='/media/',
            STATIC_URL='/static/',
            STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
            SECRET_KEY='test-secret-key',
            DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
            USE_TZ=True,
            LOGIN_URL='/accounts/login/',
            LOGIN_REDIRECT_URL='/dashboard/',
            LOGOUT_REDIRECT_URL='/accounts/login/',
            ALLOWED_IMAGE_EXTENSIONS=['jpg', 'jpeg', 'png', 'webp'],
            MAX_IMAGE_SIZE_MB=10,
            EXACT_DUPLICATE_THRESHOLD=0,
            HIGHLY_SIMILAR_THRESHOLD=5,
            POSSIBLE_DUPLICATE_THRESHOLD=10,
            MESSAGE_STORAGE='django.contrib.messages.storage.cookie.CookieStorage',
        )
