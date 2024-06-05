from pathlib import Path
from typing import Any

import requests
from django.core.management.base import BaseCommand, CommandParser

from undine.settings import undine_settings

STATIC_PATH = Path(__file__).resolve().parent.parent.parent / "static" / "undine" / "vendor"
STATIC_PATH.mkdir(parents=True, exist_ok=True)

GRAPHIQL_JS_PATH = STATIC_PATH / "graphiql.min.js"
GRAPHIQL_CSS_PATH = STATIC_PATH / "graphiql.min.css"
REACT_PATH = STATIC_PATH / "react.development.js"
REACT_DOM_PATH = STATIC_PATH / "react-dom.development.js"
EXPLORER_JS_PATH = STATIC_PATH / "plugin-explorer.umd.js"
EXPLORER_CSS_PATH = STATIC_PATH / "plugin-explorer.css"


class Command(BaseCommand):
    help = "Fetch static files required for undine"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--graphiql-version", type=str, default=undine_settings.GRAPHIQL_VERSION)
        parser.add_argument("--react-version", type=str, default=undine_settings.REACT_VERSION)
        parser.add_argument("--plugin-explorer-version", type=str, default=undine_settings.PLUGIN_EXPLORER_VERSION)

    def handle(self, *args: Any, **options: Any) -> None:
        graphiql_version = options["graphiql_version"]
        react_version = options["react_version"]
        explorer_version = options["plugin_explorer_version"]

        url_to_path: dict[str, Path] = {
            f"https://unpkg.com/graphiql@{graphiql_version}/graphiql.min.js": GRAPHIQL_JS_PATH,
            f"https://unpkg.com/graphiql@{graphiql_version}/graphiql.min.css": GRAPHIQL_CSS_PATH,
            f"https://unpkg.com/react@{react_version}/umd/react.development.js": REACT_PATH,
            f"https://unpkg.com/react-dom@{react_version}/umd/react-dom.development.js": REACT_DOM_PATH,
            f"https://unpkg.com/@graphiql/plugin-explorer@{explorer_version}/dist/index.umd.js": EXPLORER_JS_PATH,
            f"https://unpkg.com/@graphiql/plugin-explorer@{explorer_version}/dist/style.css": EXPLORER_CSS_PATH,
        }
        self.stdout.write("Fetching static files...")

        with requests.Session() as session:
            for url, path in url_to_path.items():
                self.stdout.write(f"Fetching from '{url}'")
                response = session.get(url, allow_redirects=True, timeout=15)
                response.raise_for_status()
                self.stdout.write(f"Writing contents to '{path}'")
                path.write_text(response.text, encoding="utf-8")

        self.stdout.write("Files fetched successfully!")
