from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from graphql import GraphQLArgument, GraphQLArgumentMap, GraphQLField, GraphQLList, GraphQLNonNull, GraphQLOutputType

from undine.converters import (
    convert_field_to_graphql_type,
    convert_ref_to_field_description,
    convert_ref_to_field_type,
    convert_ref_to_params,
    convert_ref_to_resolver,
    convert_to_ref,
    convert_type_to_graphql_type,
)
from undine.parsers import parse_docstring
from undine.settings import undine_settings
from undine.utils import is_pk_property, name_to_camel_case

if TYPE_CHECKING:
    from undine import ModelGQLType
    from undine.parsers.parse_docstring import DocData


__all__ = [
    "Field",
]


class Field:
    def __init__(  # noqa: PLR0913
        self,
        ref: Any,
        /,
        *,
        description: str | None = None,
        nullable: bool = False,
        many: bool = False,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a GraphQL field.

        :param ref: Reference to build the field from. Accepts inputs that can be
                    converted to known values using the `convert_to_ref` function.
        :param description: Description of the field.
        :param nullable: Whether the referenced type can be null.
        :param many: Whether the field should contain a non-null list of the referenced type.
        :param deprecation_reason: Reason for deprecating the field.
        :param extensions: Extensions for the field.
        """
        self.ref = convert_to_ref(ref)
        self.description = description
        self.nullable = nullable
        self.many = many
        self.deprecation_reason = deprecation_reason
        self.extensions: dict[str, Any] = extensions or {}
        self.extensions["undine_field"] = self

    def __set_name__(self, owner: type | type[ModelGQLType], name: str) -> None:
        self.owner = owner
        self.name = name

    def get_graphql_field(self, *, top_level: bool = False) -> GraphQLField:
        doc_data = parse_docstring(self.description or convert_ref_to_field_description(self.ref))
        resolver = convert_ref_to_resolver(self.ref, many=self.many, top_level=top_level, name=self.name)
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(doc_data=doc_data, top_level=top_level),
            resolve=resolver,
            description=doc_data.body,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLOutputType:
        if is_pk_property(self.ref):
            return convert_field_to_graphql_type(self.owner.__model__._meta.pk)

        field_type = convert_ref_to_field_type(self.ref)

        # TODO: Items not required, and list required, and vice versa?
        if not self.nullable and not isinstance(field_type, GraphQLNonNull):
            field_type = GraphQLNonNull(field_type)

        if self.many and not isinstance(field_type, GraphQLList):
            field_type = GraphQLNonNull(GraphQLList(field_type))

        return field_type

    def get_field_arguments(self, *, doc_data: DocData, top_level: bool = False) -> GraphQLArgumentMap:
        params = convert_ref_to_params(self.ref, many=self.many, top_level=top_level)
        return {
            param.name: GraphQLArgument(
                type_=convert_type_to_graphql_type(param.annotation),
                default_value=param.default_value,
                description=doc_data.arg_descriptions.get(param.name),
                deprecation_reason=doc_data.deprecation_descriptions.get(param.name),
                extensions={
                    "undine_field": self,
                },
            )
            for param in params
        }


def get_fields_from_class(cls: type | type[ModelGQLType]) -> dict[str, GraphQLField]:
    from undine import ModelGQLType

    top_level = not issubclass(cls, ModelGQLType)
    fields: list[tuple[str, Field]] = inspect.getmembers(cls, lambda x: isinstance(x, Field))

    func = name_to_camel_case if undine_settings.CAMEL_CASE_SCHEMA_FIELDS else lambda x: x
    return {func(name): field.get_graphql_field(top_level=top_level) for name, field in fields}
