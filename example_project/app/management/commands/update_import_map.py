from __future__ import annotations

import base64
import hashlib
import inspect
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from django.core.management.base import BaseCommand

from undine.http.utils import ModuleInfo

if TYPE_CHECKING:
    from undine.http.utils import ModuleInfoItem


class Command(BaseCommand):
    help = "Update GraphiQL import map."

    def handle(self, *args: Any, **options: Any) -> None:
        update_import_map()


def update_import_map() -> None:
    mapping: dict[str, str] = {
        ModuleInfo.REACT.name: sri_from_url(ModuleInfo.REACT),
        ModuleInfo.REACT_JSX_RUNTIME.name: sri_from_url(ModuleInfo.REACT_JSX_RUNTIME),
        ModuleInfo.REACT_DOM.name: sri_from_url(ModuleInfo.REACT_DOM),
        ModuleInfo.REACT_DOM_CLIENT.name: sri_from_url(ModuleInfo.REACT_DOM_CLIENT),
        ModuleInfo.GRAPHIQL.name: sri_from_url(ModuleInfo.GRAPHIQL),
        ModuleInfo.EXPLORER.name: sri_from_url(ModuleInfo.EXPLORER),
        ModuleInfo.GRAPHIQL_REACT.name: sri_from_url(ModuleInfo.GRAPHIQL_REACT),
        ModuleInfo.GRAPHIQL_TOOLKIT.name: sri_from_url(ModuleInfo.GRAPHIQL_TOOLKIT),
        ModuleInfo.GRAPHQL.name: sri_from_url(ModuleInfo.GRAPHQL),
        ModuleInfo.MONACO_EDITOR_EDITOR_WORKER.name: sri_from_url(ModuleInfo.MONACO_EDITOR_EDITOR_WORKER),
        ModuleInfo.MONACO_EDITOR_JSON_WORKER.name: sri_from_url(ModuleInfo.MONACO_EDITOR_JSON_WORKER),
        ModuleInfo.MONACO_GRAPHQL_GRAPHQL_WORKER.name: sri_from_url(ModuleInfo.MONACO_GRAPHQL_GRAPHQL_WORKER),
        ModuleInfo.GRAPHIQL_CSS.name: sri_from_url(ModuleInfo.GRAPHIQL_CSS),
        ModuleInfo.EXPLORER_CSS.name: sri_from_url(ModuleInfo.EXPLORER_CSS),
    }

    replace_integrity_in_module_info(mapping)


def sri_from_url(info: ModuleInfoItem) -> str:
    response = httpx.get(info.url)
    response.raise_for_status()
    return sri_from_content(response.content)


def sri_from_content(content: bytes) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(content).digest()).decode("utf-8")


def replace_integrity_in_module_info(mapping: dict[str, str]) -> None:
    """Replace the integrity value in the ModuleInfo class."""
    module = inspect.getmodule(ModuleInfo)
    if module is None:
        return

    filename = module.__file__
    if filename is None:
        return

    inspect.getsource(module)
    source_lines, _ = inspect.getsourcelines(module)
    lines_by_index = dict(enumerate(source_lines))

    sri: str | None = None
    for index, line in lines_by_index.items():
        if line.strip().endswith("ModuleInfoItem("):
            name = line.strip().split(" ")[0]
            sri = mapping.get(name)
            if sri is None:
                msg = f"No SRI for {name!r}"
                raise ValueError(msg)

            continue

        if line.strip().startswith("integrity="):
            if sri is None:
                msg = "SRI is None"
                raise ValueError(msg)

            lines_by_index[index] = re.sub(r'integrity=".*",', f'integrity="{sri}",', line)

            sri = None

    new_source = "".join(lines_by_index.values())
    Path(filename).resolve().write_text(new_source)
