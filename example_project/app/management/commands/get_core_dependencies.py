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
        project = data["project"]
        dependencies: list[str] = list(project["dependencies"])
        for extra in project["optional-dependencies"].values():
            dependencies.extend(extra)
        self.stdout.write(json.dumps(sorted(dependencies), indent=4))
