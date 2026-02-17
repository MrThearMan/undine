from __future__ import annotations

import json
import sys
from inspect import cleandoc
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Set up local config files (mypy.ini, pyrightconfig.json, pytest.ini)."

    def handle(self, *args: Any, **options: Any) -> None:
        root = Path(__file__).resolve().parents[4]
        venv = Path(sys.prefix)
        python_exe = Path(sys.executable)

        self.setup_mypy_ini(root, python_exe)
        self.setup_pyrightconfig(root, venv)
        self.setup_pytest_ini(root)

    def setup_mypy_ini(self, root: Path, python_exe: Path) -> None:
        path = root / "mypy.ini"
        path.write_text(
            cleandoc(
                f"""
                [mypy]
                python_executable = {python_exe}
                plugins = mypy_django_plugin.main

                [mypy.plugins.django-stubs]
                django_settings_module = example_project.project.settings
                """
            )
            + "\n"
        )
        self.stdout.write(f"Created {path}")

    def setup_pyrightconfig(self, root: Path, venv: Path) -> None:
        path = root / "pyrightconfig.json"
        data = {"venvPath": str(venv.parent), "venv": venv.name}
        path.write_text(json.dumps(data, indent=4) + "\n")
        self.stdout.write(f"Created {path}")

    def setup_pytest_ini(self, root: Path) -> None:
        path = root / "pytest.ini"
        if path.exists():
            self.stdout.write(f"{path} already exists, skipping")
            return

        path.write_text(
            cleandoc(
                """
                [pytest]
                DJANGO_SETTINGS_MODULE = example_project.project.settings
                addopts = --no-migrations --reuse-db --disable-warnings
                # addopts = --reuse-db --disable-warnings
                # addopts = --create-db --reuse-db --disable-warnings
                """
            )
            + "\n"
        )
        self.stdout.write(f"Created {path}")
