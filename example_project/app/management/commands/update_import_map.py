from __future__ import annotations

import base64
import hashlib
import inspect
import re
from pathlib import Path
from typing import Any

import httpx
from django.core.management.base import BaseCommand

from undine.integrations.graphiql import ModuleInfo, ModuleInfoItem
from undine.utils.reflection import get_members


class Command(BaseCommand):
    help = "Update GraphiQL import map."

    def handle(self, *args: Any, **options: Any) -> None:
        update_import_map()


def update_import_map() -> None:
    mapping: dict[str, str] = {}
    for name, value in get_members(ModuleInfo, ModuleInfoItem).items():
        mapping[name] = sri_from_url(value)

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
