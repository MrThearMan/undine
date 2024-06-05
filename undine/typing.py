from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from graphql import InputValueDefinitionNode


__all__ = [
    "ArgumentVariables",
]


class ArgumentVariables(TypedDict):
    default_value: Any
    description: str | None
    deprecation_reason: str | None
    out_name: str | None
    extensions: dict[str, Any] | None
    ast_node: InputValueDefinitionNode | None
