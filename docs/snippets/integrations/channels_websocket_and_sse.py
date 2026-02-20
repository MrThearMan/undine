import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "...")
django_application = get_asgi_application()

# Needs be imported after 'django_application' is created!
from undine.integrations.channels import get_websocket_and_sse_enabled_app

application = get_websocket_and_sse_enabled_app(django_application)
