"""
Django settings for the Nutrition Tracker backend.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
FRONTEND_DIST = Path(
    os.environ.get("FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist")
)

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-change-in-production-nutrition-tracker-2026",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]
if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    ALLOWED_HOSTS.append(os.environ["RAILWAY_PUBLIC_DOMAIN"])
if os.environ.get("RAILWAY_PRIVATE_DOMAIN"):
    ALLOWED_HOSTS.append(os.environ["RAILWAY_PRIVATE_DOMAIN"])
if not DEBUG and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend([".railway.app", ".up.railway.app"])

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['RAILWAY_PUBLIC_DOMAIN']}")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.accounts",
    "apps.foods",
    "apps.diary",
    "apps.subscriptions",
    "apps.mealplans",
    "apps.billing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIST] if (FRONTEND_DIST / "index.html").exists() else [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 4},
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Baghdad"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if FRONTEND_DIST.exists():
    WHITENOISE_ROOT = FRONTEND_DIST
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# SuperQI merchant wallet — users transfer directly to this number.
SUPERQI_MERCHANT_PHONE = os.environ.get("SUPERQI_MERCHANT_PHONE", "07801234567")
SUPERQI_MERCHANT_LABEL = "سوبر كي — محفظة البرنامج"

# WhatsApp expiry reminders (stored + wa.me link; plug in a provider later).
WHATSAPP_ENABLED = True
WHATSAPP_FROM_LABEL = "Nutrition Tracker"

# Card payments (PCI): never store PAN/CVV — gateway returns token + txn id only.
# mode: "sandbox" (local 3DS OTP) | "qicard" (hosted SuperQI / QiCard checkout)
PAYMENT_GATEWAY_MODE = os.environ.get("PAYMENT_GATEWAY_MODE", "sandbox")
railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
FRONTEND_BASE_URL = os.environ.get(
    "FRONTEND_BASE_URL",
    f"https://{railway_url}" if railway_url else "http://localhost:5173",
)
BACKEND_PUBLIC_URL = os.environ.get(
    "BACKEND_PUBLIC_URL",
    f"https://{railway_url}" if railway_url else "http://localhost:8000",
)
QICARD_USERNAME = os.environ.get("QICARD_USERNAME", "")
QICARD_PASSWORD = os.environ.get("QICARD_PASSWORD", "")
QICARD_TERMINAL_ID = os.environ.get("QICARD_TERMINAL_ID", "")
QICARD_API_BASE = os.environ.get("QICARD_API_BASE", "https://api-gate.qi.iq")
