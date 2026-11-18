@echo off
echo ============================================
echo   DupliDetect - Setup Script (Windows)
echo ============================================

python -m venv venv
call venv\Scripts\activate.bat

pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo Created .env from .env.example
)

python manage.py makemigrations
python manage.py migrate

python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin1234')"

python manage.py load_sample_data

echo.
echo ============================================
echo   Setup complete!
echo   Admin:  admin / admin1234
echo   Demo:   demo  / demo1234
echo   Run:    python manage.py runserver
echo ============================================
