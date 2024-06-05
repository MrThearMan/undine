from __future__ import annotations

from http import HTTPStatus
from http.client import HTTPException, HTTPSConnection
from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand

from undine.settings import undine_settings

if TYPE_CHECKING:
    from django.core.management.base import CommandParser


class Command(BaseCommand):
    help = "Fetch static files required for GraphiQL in undine"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--graphiql-version",
            type=str,
            default=undine_settings.GRAPHIQL_VERSION,
        )
        parser.add_argument(
            "--react-version",
            type=str,
            default=undine_settings.GRAPHIQL_REACT_VERSION,
        )
        parser.add_argument(
            "--plugin-explorer-version",
            type=str,
            default=undine_settings.GRAPHIQL_PLUGIN_EXPLORER_VERSION,
        )

    def handle(self, *args: Any, **options: Any) -> None:
        static_path = Path(__file__).resolve().parent.parent.parent / "static" / "undine" / "vendor"
        static_path.mkdir(parents=True, exist_ok=True)

        graphiql_version = options["graphiql_version"]
        react_version = options["react_version"]
        explorer_version = options["plugin_explorer_version"]

        url_to_path: dict[str, Path] = {
            f"/graphiql@{graphiql_version}/graphiql.min.js": static_path / "graphiql.min.js",
            f"/graphiql@{graphiql_version}/graphiql.min.css": static_path / "graphiql.min.css",
            f"/react@{react_version}/umd/react.development.js": static_path / "react.development.js",
            f"/react-dom@{react_version}/umd/react-dom.development.js": static_path / "react-dom.development.js",
            f"/@graphiql/plugin-explorer@{explorer_version}/dist/index.umd.js": static_path / "plugin-explorer.umd.js",
            f"/@graphiql/plugin-explorer@{explorer_version}/dist/style.css": static_path / "plugin-explorer.css",
        }
        self.stdout.write("Fetching static files...")

        connection = HTTPSConnection("unpkg.com", timeout=15)

        for url, path in url_to_path.items():
            self.stdout.write(f"Fetching '{connection.host}{url}'...")

            connection.request(method="GET", url=url)
            response = connection.getresponse()
            content = response.read().decode("utf-8")

            if response.status != HTTPStatus.OK:
                msg = f"[{response.status}] Failed to fetch '{connection.host}{url}': {content}"
                raise HTTPException(msg)

            self.stdout.write(f"Writing contents to '{path}'")
            path.write_text(data=content, encoding="utf-8")

        self.stdout.write("Files fetched successfully!")
