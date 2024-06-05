from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, overload

from graphql import GraphQLArgumentMap, GraphQLField, GraphQLOutputType, Undefined

from undine.converters import convert_to_graphql_type, get_argument_type
from undine.docstring import parse_description
from undine.text import check_snake_case, to_camel_case
from undine.utils import get_signature

if TYPE_CHECKING:
    from types import FunctionType

__all__ = [
    "field",
]


class field:  # noqa: N801
    """GraphQL field."""

    @overload
    def __init__(
        self,
        /,
        *,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> None:
        """Typing information when using as decorator: @field()"""

    def __init__(
        self,
        func: FunctionType | None = None,
        /,
        *,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> None:
        self.func: FunctionType = func
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions
        self.description = description

    def __call__(self, func: FunctionType, /) -> Self:
        """Overrides the func when using as decorator: @field()"""
        self.func = func
        return self

    def __set_name__(self, owner: type, name: str) -> None:
        self.owner = owner
        self.signature = get_signature(self.func)
        self.name_snake_case = check_snake_case(name)
        self.name_camel_case = to_camel_case(name)

    def __get__(self, instance: object | None, owner: type | None) -> Any:
        if instance is None:
            return self
        self.instance = instance
        return self.get_graphql_field()

    def get_graphql_field(self) -> GraphQLField:
        doc_data = parse_description(self.description or self.func.__doc__)
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(doc_data.arg_descriptions, doc_data.deprecation_descriptions),
            resolve=self.resolve,
            description=doc_data.body,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLOutputType:
        return convert_to_graphql_type(self.signature.return_annotation)

    def get_field_arguments(self, descriptions: dict[str, str], deprecations: dict[str, str]) -> GraphQLArgumentMap:
        return {
            name: get_argument_type(
                arg=param.annotation,
                default_value=param.default if param.default is not param.empty else Undefined,
                description=descriptions.get(name),
                deprecation_reason=deprecations.get(name),
                # TODO: extensions
            )
            for name, param in self.signature.parameters.items()
            if name != "self"
        }

    def resolve(self, root: object, info: Any, **kwargs: Any) -> Any:
        """Resolve the field."""
        original_info = getattr(self.instance, "info", None)
        original_root = getattr(self.instance, "root", None)
        try:
            self.instance.info = info
            self.instance.root = root
            return self.func(self.instance, **kwargs)
        finally:
            self.instance.info = original_info
            self.instance.root = original_root
