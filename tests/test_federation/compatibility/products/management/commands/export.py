from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management import BaseCommand
from graphql import GraphQLDirective, GraphQLNamedType

from undine.settings import undine_settings


def render_schema() -> str:
    return undine_settings.SDL_PRINTER.print_schema(
        undine_settings.SCHEMA,
        type_filter=type_filter,
        directive_filter=directive_filter,
        extend_schema=True,
    )


class Command(BaseCommand):
    help = "Print the GraphQL schema to stdout."

    def handle(self, *args: Any, **options: Any) -> None:
        path = settings.BASE_DIR / "schema.graphql"
        path.write_text(render_schema())
        self.stdout.write(self.style.SUCCESS(f"Schema written to {path}."))


def type_filter(named_type: GraphQLNamedType) -> bool:
    if not undine_settings.SDL_PRINTER.default_type_filter(named_type):
        return False
    return not named_type.extensions.get(undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY, False)


def directive_filter(directive: GraphQLDirective) -> bool:
    if not undine_settings.SDL_PRINTER.default_directive_filter(directive):
        return False
    return not directive.extensions.get(
        undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY, False
    ) and directive.name not in {
        "atomic",
        "complexity",
        "cacheRules",
        "semanticNonNull",
    }
