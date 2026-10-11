import os
import secrets
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")
load_dotenv(REPO_ROOT / "server" / ".env")

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    secrets.token_urlsafe(48) if os.getenv("DJANGO_DEBUG", "true").lower() == "true" else "",
)
if not SECRET_KEY:
    raise RuntimeError("Set DJANGO_SECRET_KEY before starting the production Django app.")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
CSRF_COOKIE_SECURE = not DEBUG

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "campushub.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "portal.context_processors.campushub_user",
            ],
        },
    }
]
WSGI_APPLICATION = "campushub.wsgi.application"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "campushub-files")
DJANGO_PUBLIC_URL = os.getenv("DJANGO_PUBLIC_URL", "").rstrip("/")


def postgres_settings(database_url):
    parsed = urlsplit(database_url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ValueError("DATABASE_URL must use the postgres:// or postgresql:// scheme.")
    options = dict(parse_qsl(parsed.query))
    if parsed.hostname and (
        parsed.hostname.endswith(".pooler.supabase.com")
        or parsed.hostname.endswith(".supabase.co")
    ):
        options.setdefault("sslmode", "require")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or "",
        "CONN_MAX_AGE": 0,
        "OPTIONS": options,
    }


database_url = os.getenv("DATABASE_URL")
SUPABASE_DATABASE_CONFIGURED = bool(database_url)
if database_url:
    DATABASES = {"default": postgres_settings(database_url)}
elif DEBUG:
    # Allows template and route work without credentials; no production data is stored here.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "dev.sqlite3",
        }
    }
else:
    raise RuntimeError("Set DATABASE_URL before starting the production Django app.")

LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    ("styles", REPO_ROOT / "client" / "src" / "styles"),
    ("python", BASE_DIR / "static"),
]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
