from __future__ import annotations

from typing import Any

from django.core.management import BaseCommand

from undine.settings import undine_settings


class Command(BaseCommand):
    help = "Print the GraphQL schema to stdout."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(undine_settings.SDL_PRINTER.print_schema(undine_settings.SCHEMA))
