from __future__ import annotations

from django import apps

__all__ = [
    "AppConfig",
]


class AppConfig(apps.AppConfig):
    name = "example_project.app"
