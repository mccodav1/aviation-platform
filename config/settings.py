import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Every deployment-specific value comes from the environment - see
# .env.example for the full list, split into MANDATORY and OPTIONAL.
# Under compose, env vars arrive via env_file/environment and a .env file
# is never baked into the image; for local runserver they're read from
# .env here. load_dotenv() never overrides a variable that's already set,
# so compose's and the Makefile's explicit values always win.
load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    value = os.environ.get(name, "").strip()
    return value if value else default


def env_bool(name, default=False):
    value = env(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def env_list(name, default=()):
    value = env(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


# Off unless explicitly turned on - the Makefile sets DJANGO_DEBUG=true for
# local development, compose never does.
DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")
    SECRET_KEY = "django-insecure-local-development-only"

# The IP and/or domain name(s) this deployment answers to. Moving from a
# bare IP to a real domain is just adding it here (comma-separated) and
# restarting - nginx's catch-all server block doesn't need to change.
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if DEBUG:
    ALLOWED_HOSTS += ["localhost", "127.0.0.1", "[::1]"]
elif not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set when DJANGO_DEBUG is off.")

# Only needed if a form is ever POSTed from an origin other than the one
# serving it. Same-origin requests pass Django's CSRF origin check on
# their own, including over HTTPS behind nginx (see
# SECURE_PROXY_SSL_HEADER below).
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# nginx sets X-Forwarded-Proto from the scheme it actually received, and
# gunicorn is never reachable except through nginx (compose doesn't
# publish its port), so this header can't be spoofed by a client.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Flip on once nginx terminates TLS. While the site is still served over
# plain HTTP (bare IP, no cert), these must stay off - secure-only
# cookies would make logging in impossible.
HTTPS = env_bool("DJANGO_HTTPS", False)
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
SECURE_SSL_REDIRECT = HTTPS
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30 if HTTPS else 0


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "core",
    # A required, permanent part of this template, not a toggleable/
    # pluggable app - split out from core for code organization only.
    # core uses it directly (its URLs, the home page calendar), so it
    # can't be removed.
    "meetings",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.organization.OrganizationMiddleware',
    'core.middleware.timezone.BrowserTimezoneMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.organization',
                'meetings.context_processors.meetings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Runtime state - the uploaded/admin-managed files, plus the SQLite
# database when that's what's in use. Locally this defaults to the repo
# root, so the existing db.sqlite3/media/private_media keep working;
# compose sets it to /data, where its volumes are mounted. Nothing else
# in the codebase should build a path to runtime state from BASE_DIR -
# use MEDIA_ROOT/PRIVATE_MEDIA_ROOT/DATABASES instead.
DATA_DIR = Path(env("DATA_DIR", BASE_DIR))


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# Postgres whenever POSTGRES_HOST is set (compose sets it to its own db
# service), SQLite otherwise - so a plain `make runserver` needs no
# database server at all, even with a compose-ready .env present.
if env("POSTGRES_HOST"):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': env("POSTGRES_HOST"),
            'PORT': env("POSTGRES_PORT", "5432"),
            'NAME': env("POSTGRES_DB", "aviation"),
            'USER': env("POSTGRES_USER", "aviation"),
            'PASSWORD': env("POSTGRES_PASSWORD"),
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': DATA_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

# Datetimes are always stored in UTC (USE_TZ below). Each visitor sees,
# and types, times in their own browser's timezone - see
# core/middleware/timezone.py. This is only the fallback for a request
# that hasn't reported one yet (a first visit, no JS, a bot), so it
# should be wherever the org itself is.
TIME_ZONE = env("DJANGO_TIME_ZONE", "America/Los_Angeles")

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# Where `manage.py collectstatic` gathers files for WhiteNoise to serve.
# A build artifact, not runtime state - the Dockerfile runs collectstatic
# at image build time, so it doesn't need a volume.
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"

# Gated files (meeting agendas/minutes, every Resource upload) - read by
# core/storage.py and meetings/storage.py and never given a URL route.
# Kept as a sibling of MEDIA_ROOT, not inside it, so the public media
# directory (which nginx serves directly) can never expose these.
PRIVATE_MEDIA_ROOT = DATA_DIR / "private_media"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", "INFO"),
    },
}
