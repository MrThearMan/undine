from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.core.management import BaseCommand, CommandError
from graphql import BreakingChange, DangerousChange, SafeChange, build_schema, find_schema_changes

from undine.management.commands.print_schema import get_schema_sdl

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from collections.abc import Callable, Sequence

    from graphql import SchemaChange


class Command(BaseCommand):
    help = "Compare the GraphQL schema against a previously exported SDL file and list the changes."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "path",
            nargs="?",
            default="schema.graphql",
            help="Path to the previously exported SDL file. Defaults to 'schema.graphql'.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        path = Path(options["path"])

        if not path.is_file():
            msg = f"Schema file '{path}' does not exist. Create it with `python manage.py print_schema > {path}`."
            raise CommandError(msg)

        # Both schemas are built from SDL, so that only the parts visible in the SDL are compared.
        # SDL validation is skipped, since federation SDL uses directives it doesn't define.
        old_schema = build_schema(path.read_text(encoding="utf-8"), assume_valid_sdl=True)
        new_schema = build_schema(get_schema_sdl(), assume_valid_sdl=True)

        changes = find_schema_changes(old_schema, new_schema)
        if not changes:
            self.stdout.write(self.style.SUCCESS(f"No changes compared to schema file '{path}'."))
            return

        breaking_changes = [change for change in changes if isinstance(change, BreakingChange)]
        dangerous_changes = [change for change in changes if isinstance(change, DangerousChange)]
        safe_changes = [change for change in changes if isinstance(change, SafeChange)]

        self.write_changes("Breaking changes", breaking_changes, style=self.style.ERROR)
        self.write_changes("Dangerous changes", dangerous_changes, style=self.style.WARNING)
        self.write_changes("Safe changes", safe_changes, style=self.style.SUCCESS)

        if breaking_changes:
            msg = f"Found {len(breaking_changes)} breaking change(s) compared to schema file '{path}'."
            raise CommandError(msg)

    def write_changes(self, title: str, changes: Sequence[SchemaChange], *, style: Callable[[str], str]) -> None:
        if not changes:
            return

        self.stdout.write(style(f"{title}:"))
        for change in changes:
            self.stdout.write(f"  {change.type.name}: {change.description}")
