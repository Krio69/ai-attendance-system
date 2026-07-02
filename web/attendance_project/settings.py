"""
Django settings for Face Recognition Attendance System.
Optimized for local development and Vercel deployment.
"""

import os
import sys
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # repo root

# Ensure /web is importable in Vercel/runtime
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-this-in-production-xyz123")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [".vercel.app", "localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "crispy_bootstrap5",
    "accounts",
    "academics",
    "attendance",
    "enrollment",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "attendance_project.security.SessionTimeoutMiddleware",
]

ROOT_URLCONF = "attendance_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "attendance_project.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "attendance_system",
            "USER": "postgres",
            "PASSWORD": "root123",
            "HOST": "localhost",
            "PORT": "5432",
        }
    }

AUTH_USER_MODEL = "accounts.CustomUser"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Static/Media (stable for Vercel serverless)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

ENROLLMENT_DATA_DIR = PROJECT_ROOT / "dataset" / "enrollment"
FACES_DIR = ENROLLMENT_DATA_DIR / "faces_aligned"
GALLERY_DIR = ENROLLMENT_DATA_DIR / "gallery"

RECOGNITION_THRESHOLD = 0.50
INSIGHTFACE_MODEL = "buffalo_l"
DET_SIZE = (640, 640)
DET_THRESH = 0.5

ANTI_SPOOF_ENABLED = True
ANTI_SPOOF_THRESHOLD = 0.0525
ANTI_SPOOF_MODEL_PATH = PROJECT_ROOT / "models" / "best_model.onnx"
ANTI_SPOOF_INPUT_SIZE = 128
ANTI_SPOOF_LIVE_CLASS_INDEX = 0
ANTI_SPOOF_USE_HEURISTIC_FALLBACK = True
ANTI_SPOOF_UNCERTAIN_MARGIN = 0.15
ANTI_SPOOF_DEBUG = False
ANTI_SPOOF_MIN_FACE_SIZE = 96
ANTI_SPOOF_CROP_MARGIN_RATIO = 0.12
LIVENESS_THRESHOLD = 0.85

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ATTENDANCE_REQUEST_WINDOW = 48
AUTO_SEND_ABSENCE_NOTIFICATIONS = True
NOTIFICATION_RETENTION_DAYS = 30
NOTIFICATIONS_PER_PAGE = 20

SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 4},
    },
]

CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://*.vercel.app",
]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True