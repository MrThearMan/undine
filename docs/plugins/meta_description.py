from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from mkdocs.plugins import BasePlugin

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.pages import Page


class MetaDescriptionPlugin(BasePlugin):
    """Add meta descriptions to pages if they don't already have one."""

    def on_post_page(self, output: str, /, *, page: Page, config: MkDocsConfig) -> str | None:
        description = page.meta.get("description")
        if not description:
            return output

        soup = BeautifulSoup(output, "html.parser")
        head = soup.head
        if head is None:
            return output

        desc = head.find("meta", attrs={"name": "description"})
        if desc is None:
            description_tag = soup.new_tag("meta", attrs={"name": "description", "content": description})
            head.append(description_tag)
            return str(soup)

        return output
