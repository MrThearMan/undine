from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.project.settings")
django_application = get_asgi_application()

# Needs be imported after 'django_application' is created!
from undine.integrations.channels import get_websocket_and_sse_enabled_app  # noqa: E402

application = get_websocket_and_sse_enabled_app(django_application)

# Make sure ASYNC support is enabled
from undine.settings import undine_settings  # noqa: E402

undine_settings.ASYNC = True  # type: ignore[misc]
