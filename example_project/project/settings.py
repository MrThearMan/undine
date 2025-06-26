from __future__ import annotations

import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = True
SECRET_KEY = get_random_secret_key()
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "example_project.project.urls"
WSGI_APPLICATION = "example_project.project.wsgi.application"

ALLOWED_HOSTS = []
INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS = [
    "debug_toolbar",
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "undine",
    "undine.persisted_documents",
    "example_project.example",
    "example_project.app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "project" / "testdb",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {},
    "formatters": {
        "common": {
            "()": "example_project.project.logging.DotPathFormatter",
            "fmt": "\x1b[33;20m{asctime} | {levelname} | {module}.{funcName}:{lineno} | {message}\x1b[0m",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            "style": "{",
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "common",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["stdout"],
    },
}

USE_I18N = True
LANGUAGE_CODE = "en-us"
LANGUAGES = [
    ("en", "English"),
    ("fi", "Finnish"),
]

USE_TZ = True
TIME_ZONE = "UTC"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# If you want to run "collectstatic", comment out this for the duration of the command.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,
        },
    },
    "staticfiles": {
        "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
        "OPTIONS": {
            "location": STATIC_ROOT,
            "base_url": STATIC_URL,
        },
    },
}

UNDINE = {
    "SCHEMA": "example_project.app.schema.schema",
    "GRAPHIQL_ENABLED": True,
    "FILE_UPLOAD_ENABLED": True,
    "ALLOW_DID_YOU_MEAN_SUGGESTIONS": True,
    "ALLOW_INTROSPECTION_QUERIES": True,
    "NO_ERROR_LOCATION": True,
    "ASYNC": os.getenv("ASYNC", "false").lower() == "true",
    "MIDDLEWARE": [
        "example_project.app.middleware.error_logging_middleware",
    ],
    "PARSE_HOOKS": [
        "example_project.app.hooks.ExampleHook",
    ],
    "VALIDATION_HOOKS": [
        "example_project.app.hooks.ExampleHook",
    ],
    "EXECUTION_HOOKS": [
        "example_project.app.hooks.ExampleHook",
    ],
    "OPERATION_HOOKS": [
        "example_project.app.hooks.ExampleHook",
    ],
}
