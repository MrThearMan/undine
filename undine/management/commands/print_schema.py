from typing import Any

from django.core.management import BaseCommand
from graphql import print_schema

from undine.settings import undine_settings


class Command(BaseCommand):  # TODO: Test
    help = "Print the GraphQL schema to stdout."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(print_schema(undine_settings.SCHEMA))
