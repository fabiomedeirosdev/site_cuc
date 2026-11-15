import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DJANGO_DEBUG", "1").lower() in {"1", "true", "yes"}
PRODUCTION_ORIGIN = "https://rhemacuc.com.br"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not DEBUG and not SECRET_KEY:
    raise RuntimeError("Defina DJANGO_SECRET_KEY fora do modo de desenvolvimento.")
if not SECRET_KEY:
    SECRET_KEY = "local-only-insecure-development-key"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost" if DEBUG else "rhemacuc.com.br,www.rhemacuc.com.br").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.core",
    "apps.accounts.apps.AccountsConfig",
    "apps.editorial.apps.EditorialConfig",
    "apps.content.apps.ContentConfig",
    "apps.billing.apps.BillingConfig",
    "apps.communications.apps.CommunicationsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
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
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "cuc_local"),
        "USER": os.getenv("POSTGRES_USER", "cuc_dev"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "55432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 3},
    }
}

# Nenhum e-mail sai do processo durante o desenvolvimento.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
if os.getenv("SMTP_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("SMTP_HOST", "")
EMAIL_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_HOST_USER = os.getenv("SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("SMTP_USE_TLS", "1") == "1"
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "nao-responder@example.invalid")
BILLING_ENABLED = os.getenv("BILLING_ENABLED", "0") == "1"
NEWSLETTER_ENABLED = os.getenv("NEWSLETTER_ENABLED", "0") == "1"
PAGBANK_ENVIRONMENT = os.getenv("PAGBANK_ENVIRONMENT", "sandbox")
if PAGBANK_ENVIRONMENT not in {"sandbox", "production"}:
    raise RuntimeError("PAGBANK_ENVIRONMENT deve ser sandbox ou production.")
PAGBANK_CHECKOUT_TOKEN = os.getenv("PAGBANK_CHECKOUT_TOKEN", "")
PAGBANK_RECURRING_TOKEN = os.getenv("PAGBANK_RECURRING_TOKEN", "")
PUBLIC_FRONTEND_URL = os.getenv("PUBLIC_FRONTEND_URL", "http://127.0.0.1:5173" if DEBUG else PRODUCTION_ORIGIN).rstrip("/")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000" if DEBUG else PRODUCTION_ORIGIN).rstrip("/")
SUBSCRIPTION_AMOUNT_CENTS = 4800
BILLING_LEGAL_VERSION = "2026-11-12-v1"
MERCHANT_LEGAL_NAME = os.getenv("MERCHANT_LEGAL_NAME", "")
MERCHANT_DOCUMENT = os.getenv("MERCHANT_DOCUMENT", "")
MERCHANT_CONTACT_EMAIL = os.getenv("MERCHANT_CONTACT_EMAIL", "")
MERCHANT_ADDRESS = os.getenv("MERCHANT_ADDRESS", "")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(os.getenv("DJANGO_STATIC_ROOT", str(BASE_DIR.parents[1] / ".local" / "static")))
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR.parents[1] / ".local" / "media")))
COMMUNICATIONS_MEDIA_ROOT = Path(os.getenv("COMMUNICATIONS_MEDIA_ROOT", str(BASE_DIR.parents[1] / ".local" / "communications-media")))
PROFILE_MEDIA_ROOT = Path(os.getenv("PROFILE_MEDIA_ROOT", str(BASE_DIR.parents[1] / ".local" / "profile-media")))
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173" if DEBUG else PRODUCTION_ORIGIN,
    ).split(",")
    if origin.strip()
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/minute",
        "account": "120/minute",
        "password_change": "10/hour",
        "email_change": "10/hour",
        "checkout": "10/hour",
        "invitation": "20/hour",
        "billing_webhook": "120/minute",
        "newsletter": "10/hour",
    },
}

AUTHENTICATION_BACKENDS = ["apps.accounts.backends.EmailBackend"]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 12 * 60 * 60
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", ",".join(CORS_ALLOWED_ORIGINS)).split(",") if origin.strip()]
CORS_ALLOW_CREDENTIALS = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "1") == "1"

# Habilitar somente com o proxy configurado para sobrescrever esse cabeçalho
# e com o servidor Django acessível apenas pela rede privada/loopback.
if os.getenv("DJANGO_TRUST_PROXY_HEADERS", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
