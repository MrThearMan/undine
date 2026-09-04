from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = False
SECRET_KEY = "test-secret-key"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "products.User"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "undine",
    "products",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
        "NAME": "file:federationdb?mode=memory&cache=shared",
        "OPTIONS": {
            "timeout": 20,
        },
    },
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

USE_TZ = True
TIME_ZONE = "UTC"

UNDINE = {
    "SCHEMA": "products.schema.schema",
    "ASYNC": False,
    "AUTOGENERATION": False,
    "GRAPHIQL_ENABLED": True,
    "GRAPHQL_PATH": "",
    "MAX_QUERY_COMPLEXITY": 999,
    # Pinned to match Apollo's canonical reference `products.graphql` and to stay within the
    # federation spec range that Apollo's `supergraph` rover plugin (currently v2.7.1, bundled
    # with the `apollographql/federation-subgraph-compatibility` action) accepts. Newer versions
    # cause the harness to fail composition with `Unknown directive` errors.
    "FEDERATION_VERSION": "2.3",
    "INCLUDE_ERROR_TRACEBACK": True,
    "ALLOW_DID_YOU_MEAN_SUGGESTIONS": True,
    "ALLOW_INTROSPECTION_QUERIES": True,
    "ADDITIONAL_LIFECYCLE_HOOKS": [
        "undine.federation.tracing.FederatedTracingHook",
    ],
}
