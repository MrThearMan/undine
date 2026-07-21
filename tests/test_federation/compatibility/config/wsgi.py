from __future__ import annotations

import os
import sys
from pathlib import Path

base_dir = str(Path(__file__).resolve().parent.parent)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402

call_command("migrate")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
