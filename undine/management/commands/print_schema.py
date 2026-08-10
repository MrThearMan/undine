from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.core.management import BaseCommand, CommandError

from undine.settings import undine_settings

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Print the GraphQL schema to stdout."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--check",
            nargs="?",
            const="schema.graphql",
            default=None,
            metavar="PATH",
            help=(
                "Compare the schema against a previously exported SDL file instead of printing it. "
                "Exits with a non-zero status if they differ. Defaults to 'schema.graphql'."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        sdl = get_schema_sdl()

        schema_file: str | None = options["check"]
        if schema_file is None:
            self.stdout.write(sdl)
            return

        path = Path(schema_file)

        if not path.is_file():
            msg = f"Schema file '{path}' does not exist. Create it with `python manage.py print_schema > {path}`."
            raise CommandError(msg)

        if path.read_text(encoding="utf-8").strip() != sdl.strip():
            msg = f"Schema file '{path}' is out of date. Update it with `python manage.py print_schema > {path}`."
            raise CommandError(msg)

        self.stdout.write(self.style.SUCCESS(f"Schema file '{path}' is up to date."))


def get_schema_sdl() -> str:
    """
    Get the SDL for the given schema.

    For a federation schema this is the subgraph SDL served by `Query._service`,
    which is what a router or a schema registry expects.
    """
    federation_sdl: str | None = undine_settings.SCHEMA.extensions.get(undine_settings.FEDERATION_SDL_EXTENSIONS_KEY)
    if federation_sdl is not None:
        return federation_sdl

    return undine_settings.SDL_PRINTER.print_schema(undine_settings.SCHEMA)
