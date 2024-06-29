from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import GraphQLArgumentMap, GraphQLField, GraphQLOutputType, Undefined

from undine.converters import (
    convert_model_field_to_graphql_output_type,
    convert_ref_to_field_description,
    convert_ref_to_graphql_argument_map,
    convert_ref_to_graphql_output_type,
    convert_ref_to_resolver,
    convert_to_ref,
    is_ref_many,
    is_ref_nullable,
)
from undine.settings import undine_settings
from undine.utils import get_members, get_schema_name, is_pk_property

if TYPE_CHECKING:
    from undine import ModelGQLType
    from undine.optimizer.optimizer import QueryOptimizer


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
        nullable: bool = Undefined,
        many: bool = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a GraphQL field.

        :param ref: Reference to build the field from. Accepts inputs that can be
                    converted to known values using `convert_to_ref`.
        :param description: Description for the field. If not provided, the field will try
                            to find the description from the converted reference.
        :param nullable: Whether the referenced type can be null. If not provided, the field
                         will try to determine the nullability from the converted reference.
        :param many: Whether the field should contain a non-null list of the referenced type.
                     If not provided, the field will try to determine the many from the
                     converted reference.
        :param deprecation_reason: If the field is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the field.
        """
        self.ref = convert_to_ref(ref)
        self.description = description
        self.nullable = nullable if nullable is not Undefined else is_ref_nullable(self.ref)
        self.many = many if many is not Undefined else is_ref_many(self.ref)
        self.deprecation_reason = deprecation_reason
        self.extensions: dict[str, Any] = extensions or {}
        self.extensions[undine_settings.FIELD_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type | type[ModelGQLType], name: str) -> None:
        self.owner = owner
        self.name = name

    def get_graphql_field(self, *, top_level: bool = False) -> GraphQLField:
        self.description = self.description or convert_ref_to_field_description(self.ref)
        resolver = convert_ref_to_resolver(self.ref, many=self.many, top_level=top_level, name=self.name)
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(top_level=top_level),
            resolve=resolver,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLOutputType:
        if is_pk_property(self.ref):
            return convert_model_field_to_graphql_output_type(self.owner.__model__._meta.pk)
        return convert_ref_to_graphql_output_type(self.ref, many=self.many, nullable=self.nullable)

    def get_field_arguments(self, *, top_level: bool = False) -> GraphQLArgumentMap:
        arg_map = convert_ref_to_graphql_argument_map(self.ref, many=self.many, top_level=top_level)
        for arg in arg_map.values():
            arg.extensions[undine_settings.FIELD_EXTENSIONS_KEY] = self
        return arg_map

    def optimizer_hook(self, optimizer: QueryOptimizer) -> Any: ...


def get_fields_from_class(cls: type | type[ModelGQLType], *, top_level: bool = False) -> dict[str, GraphQLField]:
    fields = get_members(cls, Field)
    return {get_schema_name(name): field.get_graphql_field(top_level=top_level) for name, field in fields}
