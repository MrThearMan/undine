"""Different fields for use with the different ModelGraphQL-classes."""

from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any, Literal

from django.db import models
from graphql import (
    GraphQLArgumentMap,
    GraphQLField,
    GraphQLFieldResolver,
    GraphQLInputField,
    GraphQLInputType,
    GraphQLOutputType,
    Undefined,
)

from undine.converters import (
    convert_entrypoint_ref_to_graphql_argument_map,
    convert_entrypoint_ref_to_resolver,
    convert_field_ref_to_graphql_argument_map,
    convert_field_ref_to_resolver,
    convert_filter_ref_to_filter_resolver,
    convert_ref_to_graphql_input_type,
    convert_ref_to_graphql_output_type,
    convert_to_description,
    convert_to_field_ref,
    convert_to_filter_ref,
    convert_to_input_ref,
    convert_to_ordering_ref,
    is_field_nullable,
    is_input_required,
    is_many,
)
from undine.settings import undine_settings
from undine.utils.reflection import cache_signature_if_function
from undine.utils.unsorted import maybe_list_or_non_null

if TYPE_CHECKING:
    from undine import ModelGQLFilter, ModelGQLMutation, ModelGQLOrdering, ModelGQLType
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.typing import EntrypointRef, GQLInfo, Self

__all__ = [
    "Entrypoint",
    "Field",
    "Filter",
    "Input",
    "Ordering",
]


class Entrypoint:
    def __init__(
        self,
        ref: EntrypointRef,
        *,
        many: bool = False,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        Designate a new entrypoint in the GraphQL Schema for a query or mutation.

        :param ref: Reference to the ModelGQLType or ModelGQLMutation to use as the entrypoint.
        :param many: Whether the entrypoint should return a list of the referenced type.
                     For function based entrypoints, this is determined from the function's return type.
        :param description: Description for the entrypoint. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the entrypoint is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the entrypoint.
        """
        self.ref = cache_signature_if_function(ref, depth=1)
        self.many = many
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.ENTRYPOINT_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type, name: str) -> None:
        self.owner = owner
        self.name = name

        if isinstance(self.ref, FunctionType):
            self.many = is_many(self.ref)
        if self.description is Undefined:
            self.description = convert_to_description(self.ref)

    def __call__(self, _ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Entrypoint()"""
        self.ref = cache_signature_if_function(_ref, depth=1)
        return self

    def get_graphql_field(self) -> GraphQLField:
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(),
            resolve=self.get_resolver(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLOutputType:
        graphql_type, nullable = convert_ref_to_graphql_output_type(self.ref, return_nullable=True)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=not nullable)

    def get_field_arguments(self) -> GraphQLArgumentMap:
        return convert_entrypoint_ref_to_graphql_argument_map(self.ref, many=self.many)

    def get_resolver(self) -> GraphQLFieldResolver:
        return convert_entrypoint_ref_to_resolver(self.ref, many=self.many)


class Field:
    def __init__(
        self,
        ref: Any = None,
        *,
        many: bool = Undefined,
        nullable: bool = Undefined,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a GraphQL field.

        :param ref: Reference to build the field from. Can be anything that `convert_to_field_ref` can convert,
                    e.g., a string referencing a model field name, a model field, an expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `ModelGQLType` class.
        :param many: Whether the field should contain a non-null list of the referenced type.
                     If not provided, looks at the reference and tries to determine this from it.
        :param nullable: Whether the referenced type can be null. If not provided, looks at the converted
                         reference and tries to determine nullability from it.
        :param description: Description for the field. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the field is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the field.
        """
        self.ref = cache_signature_if_function(ref, depth=1)
        self.many = many
        self.nullable = nullable
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions: dict[str, Any] = extensions or {}
        self.extensions[undine_settings.FIELD_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type | type[ModelGQLType], name: str) -> None:
        self.owner = owner
        self.name = name
        self.ref = convert_to_field_ref(self.ref, caller=self)

        if self.many is Undefined:
            self.many = is_many(self.ref, model=self.owner.__model__, name=self.name)
        if self.nullable is Undefined:
            self.nullable = is_field_nullable(self.ref)
        if self.description is Undefined:
            self.description = convert_to_description(self.ref)

    def __call__(self, _ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Field()"""
        self.ref = cache_signature_if_function(_ref, depth=1)
        return self

    def get_graphql_field(self) -> GraphQLField:
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(),
            resolve=self.get_resolver(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLOutputType:
        graphql_type = convert_ref_to_graphql_output_type(self.ref)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=not self.nullable)

    def get_field_arguments(self) -> GraphQLArgumentMap:
        return convert_field_ref_to_graphql_argument_map(self.ref, many=self.many)

    def get_resolver(self) -> GraphQLFieldResolver:
        return convert_field_ref_to_resolver(self.ref, many=self.many, name=self.name)

    def optimizer_hook(self, optimizer: QueryOptimizer) -> None:
        """Hook for customizing how the field is optimized by the QueryOptimizer."""
        if isinstance(self.ref, (models.Expression, models.Subquery)):
            optimizer.annotations[self.name] = self.ref


class Filter:
    def __init__(
        self,
        ref: Any = None,
        *,
        lookup_expr: str = "exact",
        many: bool = False,
        distinct: bool = False,
        required: bool = False,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a `GraphQLInputType` used for filtering a `ModelGQLType`.

        :param ref: Expression to filter by. Can be anything that `convert_to_filter_ref` can convert:
                    a string referencing a model field name, an expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `ModelGQLFilter` class.
        :param lookup_expr: Lookup expression to use for the filter.
        :param many: Whether the filter requires the input to be a list of values. If not provided,
                     looks at the lookup expression and tries to determine this from it.
        :param distinct: Whether the filter requires `queryset.distinct()` to be used.
        :param required: Whether the filter should be required.
        :param description: Description of the filter. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the filter is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the filter.
        """
        self.ref = cache_signature_if_function(ref, depth=1)
        self.lookup_expr = lookup_expr
        self.many = many or lookup_expr in ("in", "range")
        self.distinct = distinct
        self.required = required
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.FILTER_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[ModelGQLFilter], name: str) -> None:
        self.owner = owner
        self.name = name
        self.ref = convert_to_filter_ref(self.ref, caller=self)

        if self.description is Undefined:
            self.description = convert_to_description(self.ref)

        self.resolver = convert_filter_ref_to_filter_resolver(self.ref, lookup_expr=self.lookup_expr, name=name)

    def __call__(self, _ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Filter()"""
        self.ref = cache_signature_if_function(_ref, depth=1)
        return self

    def get_expression(self, value: Any, info: GQLInfo) -> models.Q:
        return self.resolver(self.owner, info, value=value)

    def as_input_field(self) -> GraphQLInputField:
        return GraphQLInputField(
            type_=self.get_field_type(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLInputType:
        graphql_type = convert_ref_to_graphql_input_type(self.ref, model=self.owner.__model__)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=self.required)


class Ordering:
    def __init__(
        self,
        ref: Any = None,
        *,
        null_order: Literal["first", "last"] | None = None,
        supports_reversing: bool = True,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a GraphQL argument used for ordering a `ModelGQLType`.

        :param ref: Expression to order by. Can be anything that `convert_to_ordering_ref` can convert,
                    e.g., a string referencing a model field name, an `F` expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `ModelGQLOrdering` class.
        :param null_order: Where should null values be ordered? By default, use database default.
        :param supports_reversing: Whether the ordering supports both ascending and descending order.
                                   If `True`, this ordering will only add one option for decending order
                                   to the ordering filter instead of ascending and descending variants.
        :param description: Description of the ordering. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If this ordering is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the ordering.
        """
        self.ref = ref
        self.description = description
        self.nulls_first = True if null_order == "first" else None
        self.nulls_last = True if null_order == "last" else None
        self.supports_reversing = supports_reversing
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.ORDER_BY_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[ModelGQLOrdering], name: str) -> None:
        self.owner = owner
        self.name = name
        self.ref = convert_to_ordering_ref(self.ref, caller=self)

        if self.description is Undefined:
            self.description = convert_to_description(self.ref)

    def get_expression(self, *, descending: bool = False) -> models.OrderBy:
        return models.OrderBy(self.ref, nulls_first=self.nulls_first, nulls_last=self.nulls_last, descending=descending)


class Input:
    def __init__(
        self,
        ref: Any = None,
        *,
        many: bool = Undefined,
        required: bool = Undefined,
        input_only: bool = False,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a GraphQL input type.

        :param ref: Reference to build the input from. Can be anything that `convert_to_input_ref` can convert,
                    e.g., a string referencing a model field name, a model field, a `ModelGQLMutation`, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `ModelGQLMutation` class.
        :param many: Whether the input should contain a non-null list of the referenced type.
                     If not provided, looks at the reference and tries to determine this from it.
        :param required: Whether the input should be required. If not provided, looks at the reference
                         and the ModelGQLMutation's mutation kind to determine this.
        :param input_only: If `True`, the input's value is not included when the mutation is performed.
                           Value still exists for the pre and post mutation hooks.
        :param description: Description for the input. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the input is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the input.
        """
        self.ref = ref
        self.many = many
        self.required = required
        self.input_only = input_only
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.INPUT_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[ModelGQLMutation], name: str) -> None:
        self.owner = owner
        self.name = name
        self.ref = convert_to_input_ref(self.ref, caller=self)

        if self.many is Undefined:
            self.many = is_many(self.ref, model=self.owner.__model__, name=self.name)
        if self.required is Undefined:
            self.required = is_input_required(self.ref, caller=self)
        if self.description is Undefined:
            self.description = convert_to_description(self.ref)

    def as_input_field(self, *, entrypoint: bool = True) -> GraphQLInputField:
        return GraphQLInputField(
            type_=self.get_field_type(entrypoint=entrypoint),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self, *, entrypoint: bool = True) -> GraphQLInputType:
        graphql_type = convert_ref_to_graphql_input_type(self.ref, model=self.owner.__model__, entrypoint=entrypoint)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=self.required if entrypoint else False)
