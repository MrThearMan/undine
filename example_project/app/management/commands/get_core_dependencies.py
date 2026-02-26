from __future__ import annotations

import json
import tomllib
from typing import Any

from django.conf import settings
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Get minimum core dependencies."

    def handle(self, *args: Any, **options: Any) -> None:
        path = settings.BASE_DIR.parent / "pyproject.toml"
        data = tomllib.loads(path.read_text())
        dependencies = data["tool"]["poetry"]["dependencies"]
        self.stdout.write(json.dumps(dependencies, indent=4, sort_keys=True))
