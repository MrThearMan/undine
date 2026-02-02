from __future__ import annotations

import os

from granian import Granian
from granian.constants import Interfaces

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.project.settings")
    Granian(
        target="example_project.project.asgi:application",
        port=8000,
        interface=Interfaces.ASGI,
        log_level="error",
    ).serve()
