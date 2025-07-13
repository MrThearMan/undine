from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mkdocs.plugins import BasePlugin

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig


BASE_URLS = [
    #
    # Home page
    "",
    #
    # Missing page
    "404.html",
    #
    # CSS
    "css/docs.css",
    "css/pygments.css",
    "css/theme.css",
    "css/theme_extra.css",
    #
    # JS
    "js/docs.js",
    "js/theme.js",
    "js/theme_extra.js",
    #
    # Favicon
    "img/favicon.ico",
    #
    # Search
    "search.html",
    "search/lunr.js",
    "search/main.js",
    "search/search_index.json",
    "search/worker.js",
]


class GenerateServiceWorkerUrlsPlugin(BasePlugin):
    """Generate the URLs for the service worker."""

    def on_post_build(self, config: MkDocsConfig, **kwargs: Any) -> None:
        """Build the URLs for the service worker."""
        nav: list[dict[str, str]] = config.nav  # type: ignore[assignment]

        files = (val for item in nav for val in item.values() if val != "index.md")
        urls_to_cache = BASE_URLS + [file.replace(".md", "/") for file in files]

        site_dir = Path(config.site_dir).resolve()
        service_worker_file = site_dir / "service-worker.js"

        if not service_worker_file.exists():
            msg = f"Service worker file not found: {service_worker_file}"
            raise FileNotFoundError(msg)

        if not service_worker_file.is_file():
            msg = f"Service worker file is not a file: {service_worker_file}"
            raise FileNotFoundError(msg)

        file_data = service_worker_file.read_text(encoding="utf-8")

        # New cache name so that new builds don't use the old cache
        file_data = file_data.replace("__CACHE_NAME__", json.dumps(uuid.uuid4().hex))

        # Write the URLs to the service worker file
        file_data = file_data.replace("__URLS_TO_CACHE__", json.dumps(urls_to_cache, indent=2))

        service_worker_file.write_text(file_data, encoding="utf-8")
