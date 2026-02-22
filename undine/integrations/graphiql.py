from __future__ import annotations

import dataclasses
import json
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from django.shortcuts import render

from undine.settings import undine_settings

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


__all__ = [
    "render_graphiql",
]


def render_graphiql(request: HttpRequest) -> HttpResponse:
    """Render GraphiQL."""
    return render(request, "undine/graphiql.html", context=get_graphiql_context())


class ModuleVersion(StrEnum):
    # Note that changing the versions here will break integrity checks!
    # Integrity values can be generated using the `update_import_map` management command.

    REACT = "19.2.4"
    GRAPHIQL = "5.2.2"
    EXPLORER = "5.1.1"
    GRAPHIQL_REACT = "0.37.3"
    GRAPHIQL_TOOLKIT = "0.11.3"
    GRAPHQL = "16.12.0"
    GRAPHQL_SSE = "2.6.0"


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ModuleInfoItem:
    latest: str
    """URL to the latest version of the module."""

    version: ModuleVersion
    """Version of the module to use."""

    integrity: str
    """Subresource integrity hash for the module using the given version."""

    standalone: bool = False
    """
    Whether to bundle the module along with all of its `dependencies`,
    excluding `peerDependencies`, into a single JavaScript file.
    """

    external: list[str] = dataclasses.field(default_factory=list)
    """Dependencies that do not need to be imported as they are provided by the host environment."""

    @property
    def url(self) -> str:
        url = self.latest.replace("@latest", f"@{self.version.value}")  # type: ignore[arg-type]
        if self.standalone:
            url += "?standalone"
        if self.external:
            url += f"&external={','.join(self.external)}"
        return url


class ModuleInfo:
    REACT = ModuleInfoItem(
        latest="https://esm.sh/react@latest/",
        version=ModuleVersion.REACT,
        integrity="sha384-w+4QrjFjcEk/AIJMWVUzEOT0QT/s+K0xDQulhBdT/j9PWKIG08nWLFD90h0Yuj5R",
    )
    REACT_DOM = ModuleInfoItem(
        latest="https://esm.sh/react-dom@latest/",
        version=ModuleVersion.REACT,
        integrity="sha384-RWUKf5R/P6U794/65YB+OKpYxJbldLkbnJSNjiByqjgea+hKkDK6vnJ2qut4Lf7W",
    )
    GRAPHIQL = ModuleInfoItem(
        latest="https://esm.sh/graphiql@latest/",
        version=ModuleVersion.GRAPHIQL,
        integrity="sha384-MBVZMq1pmz8DwpwIWPWLk2tmS6tGiSi6WwbXvy9NhuDYASAAWd2m96xbxLqszig9",
    )
    GRAPHIQL_STANDALONE = ModuleInfoItem(
        latest="https://esm.sh/graphiql@latest/",
        version=ModuleVersion.GRAPHIQL,
        integrity="sha384-SzHBEbcQfhvmwqh5Vtat9k7b/kIzmdVO3KMzQiAYwcxCA9x7vZwFRUgjzN1AeV3q",
        standalone=True,
        external=["react", "react-dom", "@graphiql/react", "graphql"],
    )
    EXPLORER = ModuleInfoItem(
        latest="https://esm.sh/@graphiql/plugin-explorer@latest/",
        version=ModuleVersion.EXPLORER,
        integrity="sha384-rR9phbzRkwb/HINixBgg9De/Z/S6G9/OiRX7cVR1AKhP+2AUTfX7wmDT76y5HeSf",
        standalone=True,
        external=["react", "@graphiql/react", "graphql"],
    )
    GRAPHIQL_REACT = ModuleInfoItem(
        latest="https://esm.sh/@graphiql/react@latest/",
        version=ModuleVersion.GRAPHIQL_REACT,
        integrity="sha384-iZsbTy9B0VcX2BOTdqMuX0uJ9Hff5GbG2QeOt4OeMp0GHza76dwQaYQYNYkZkIVq",
        standalone=True,
        external=["react", "react-dom", "graphql", "@graphiql/toolkit", "@emotion/is-prop-valid"],
    )
    GRAPHIQL_TOOLKIT = ModuleInfoItem(
        latest="https://esm.sh/@graphiql/toolkit@latest/",
        version=ModuleVersion.GRAPHIQL_TOOLKIT,
        integrity="sha384-ZsnupyYmzpNjF1Z/81zwi4nV352n4P7vm0JOFKiYnAwVGOf9twnEMnnxmxabMBXe",
        standalone=True,
        external=["graphql"],
    )
    GRAPHQL = ModuleInfoItem(
        latest="https://esm.sh/graphql@latest/",
        version=ModuleVersion.GRAPHQL,
        integrity="sha384-Oosnx71vGzeLRLBj0HblPGTSLgNCn3tEUKVdBubTBLQ9xAW9538VZvjesbp8unrb",
    )
    GRAPHQL_SSE = ModuleInfoItem(
        latest="https://esm.sh/graphql-sse@latest/",
        version=ModuleVersion.GRAPHQL_SSE,
        integrity="sha384-nEeDIuZvbQI4moJ8CGRos6s2sPL7jfwBZ4ZuaZm/sw/HNxGzVOfk6g89+8LBsUNT",
    )
    GRAPHIQL_CSS = ModuleInfoItem(
        latest="https://esm.sh/graphiql@latest/dist/style.css/",
        version=ModuleVersion.GRAPHIQL,
        integrity="sha384-f6GHLfCwoa4MFYUMd3rieGOsIVAte/evKbJhMigNdzUf52U9bV2JQBMQLke0ua+2",
    )
    EXPLORER_CSS = ModuleInfoItem(
        latest="https://esm.sh/@graphiql/plugin-explorer@latest/dist/style.css/",
        version=ModuleVersion.EXPLORER,
        integrity="sha384-vTFGj0krVqwFXLB7kq/VHR0/j2+cCT/B63rge2mULaqnib2OX7DVLUVksTlqvMab",
    )


def get_graphiql_context() -> dict[str, Any]:
    """Get the GraphiQL context."""
    return {
        "http_path": undine_settings.GRAPHQL_PATH,
        "ws_path": undine_settings.WEBSOCKET_PATH,
        "sse_enabled": undine_settings.GRAPHIQL_SSE_ENABLED,
        "sse_single_connection": undine_settings.GRAPHIQL_SSE_SINGLE_CONNECTION,
        "importmap": get_importmap(),
        "graphiql_css": ModuleInfo.GRAPHIQL_CSS.url,
        "explorer_css": ModuleInfo.EXPLORER_CSS.url,
        "graphiql_css_integrity": ModuleInfo.GRAPHIQL_CSS.integrity,
        "explorer_css_integrity": ModuleInfo.EXPLORER_CSS.integrity,
    }


def get_importmap() -> str:
    """Get the importmap for GraphiQL."""
    importmap = {
        "imports": {
            "react": ModuleInfo.REACT.url,
            "react/": ModuleInfo.REACT.url,
            "react-dom": ModuleInfo.REACT_DOM.url,
            "react-dom/": ModuleInfo.REACT_DOM.url,
            "graphiql": ModuleInfo.GRAPHIQL_STANDALONE.url,
            "graphiql/": ModuleInfo.GRAPHIQL.url,
            "@graphiql/plugin-explorer": ModuleInfo.EXPLORER.url,
            "@graphiql/react": ModuleInfo.GRAPHIQL_REACT.url,
            "@graphiql/toolkit": ModuleInfo.GRAPHIQL_TOOLKIT.url,
            "graphql": ModuleInfo.GRAPHQL.url,
            "graphql-sse": ModuleInfo.GRAPHQL_SSE.url,
            "@emotion/is-prop-valid": "data:text/javascript,",
        },
        "integrity": {
            ModuleInfo.REACT.url: ModuleInfo.REACT.integrity,
            ModuleInfo.REACT_DOM.url: ModuleInfo.REACT_DOM.integrity,
            ModuleInfo.GRAPHIQL.url: ModuleInfo.GRAPHIQL.integrity,
            ModuleInfo.GRAPHIQL_STANDALONE.url: ModuleInfo.GRAPHIQL_STANDALONE.integrity,
            ModuleInfo.EXPLORER.url: ModuleInfo.EXPLORER.integrity,
            ModuleInfo.GRAPHIQL_REACT.url: ModuleInfo.GRAPHIQL_REACT.integrity,
            ModuleInfo.GRAPHIQL_TOOLKIT.url: ModuleInfo.GRAPHIQL_TOOLKIT.integrity,
            ModuleInfo.GRAPHQL.url: ModuleInfo.GRAPHQL.integrity,
            ModuleInfo.GRAPHQL_SSE.url: ModuleInfo.GRAPHQL_SSE.integrity,
        },
    }
    return json.dumps(importmap, indent=2)
