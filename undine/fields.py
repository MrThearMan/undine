# ruff: noqa: PLR0913
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from django.db import models
from graphql import (
    GraphQLArgumentMap,
    GraphQLField,
    GraphQLFieldResolver,
    GraphQLInputField,
    GraphQLInputType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLOutputType,
    GraphQLResolveInfo,
    Undefined,
)

from undine.converters import (
    convert_entrypoint_ref_to_resolver,
    convert_field_ref_to_graphql_argument_map,
    convert_field_ref_to_resolver,
    convert_filter_ref_to_filter_func,
    convert_model_field_to_graphql_output_type,
    convert_ordering_ref_to_ordering_func,
    convert_ref_to_field_description,
    convert_ref_to_graphql_input_type,
    convert_ref_to_graphql_output_type,
    convert_to_field_ref,
    convert_to_filter_ref,
    convert_to_ordering_ref,
    is_field_ref_many,
    is_field_ref_nullable,
)
from undine.converters.any_to_input_ref import convert_to_input_ref
from undine.settings import undine_settings
from undine.utils.defer import DeferredModelField
from undine.utils.reflection import cache_signature
from undine.utils.resolvers import is_pk_property

if TYPE_CHECKING:
    from types import FunctionType

    from undine.model_graphql import ModelGQLFilter, ModelGQLMutation, ModelGQLOrdering, ModelGQLType
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.typing import EntrypointRef, Self

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
        ref: EntrypointRef | None = None,
        *,
        many: bool = Undefined,
        nullable: bool = Undefined,
        description: str | None = None,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        Designate a new entrypoint in the GraphQL Schema for a query or a mutation.

        :param ref: Reference to the ModelGQLType, ModelGQLMutation, or function to use as the entrypoint.
        :param many: Whether the entrypoint should return a list of the referenced type.
                     If not provided, looks at the reference and tries to determine this from it.
        :param nullable: Whether the referenced type can be null. If not provided, looks at the
                         reference and tries to determine nullability from it.
        :param description: Description for the entrypoint. If not provided, looks at the reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the entrypoint is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the entrypoint.
        """
        cache_signature(ref, depth=1)
        self.ref = ref
        self.many = many
        self.nullable = nullable
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.ENTRYPOINT_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type, name: str) -> None:
        if self.ref is None:
            msg = "Entrypoint reference not given. Must provide reference, or use as a decorator for a function."
            raise ValueError(msg)  # TODO: Custom exception

        if self.description is Undefined:
            self.description = convert_ref_to_field_description(self.ref)
        if self.many is Undefined:
            self.many = is_field_ref_many(self.ref)
        if self.nullable is Undefined:
            self.nullable = is_field_ref_nullable(self.ref)

    def __call__(self, _ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Entrypoint()"""
        cache_signature(_ref, depth=1)
        self.ref = _ref
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
        return convert_ref_to_graphql_output_type(self.ref, many=self.many, nullable=self.nullable)

    def get_field_arguments(self) -> GraphQLArgumentMap:
        return convert_field_ref_to_graphql_argument_map(self.ref, many=self.many)

    def get_resolver(self) -> GraphQLFieldResolver:
        return convert_entrypoint_ref_to_resolver(self.ref, many=self.many)


class Field:
    def __init__(
        self,
        ref: Any = None,
        *,
        nullable: bool = Undefined,
        many: bool = Undefined,
        description: str | None = None,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a GraphQL field.

        :param ref: Reference to build the field from. Can be anything that `convert_to_field_ref` can convert,
                    e.g., a string referencing a model field name, a model field, a function, a property, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `ModelGQLType` class.
        :param nullable: Whether the referenced type can be null. If not provided, looks at the converted
                         reference and tries to determine nullability from it.
        :param many: Whether the field should contain a non-null list of the referenced type.
                     If not provided, looks at the reference and tries to determine this from it.
        :param description: Description for the field. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the field is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the field.
        """
        cache_signature(ref, depth=1)
        self.ref = convert_to_field_ref(ref)
        self.description = description
        self.nullable = nullable
        self.many = many
        self.deprecation_reason = deprecation_reason
        self.extensions: dict[str, Any] = extensions or {}
        self.extensions[undine_settings.FIELD_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type | type[ModelGQLType], name: str) -> None:
        self.owner = owner
        self.name = name

        if self.ref == "self":
            self.ref = owner

        if isinstance(self.ref, DeferredModelField):
            self.ref = self.ref.get_field(self.owner.__model__, self.ref.name or name)
            self.ref = convert_to_field_ref(self.ref)

        if self.description is None:
            self.description = convert_ref_to_field_description(self.ref)
        if self.nullable is Undefined:
            self.nullable = is_field_ref_nullable(self.ref)
        if self.many is Undefined:
            self.many = is_field_ref_many(self.ref)

    def __call__(self, _ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Field()"""
        cache_signature(_ref, depth=1)
        self.ref = convert_to_field_ref(_ref)
        return self

    def get_graphql_field(self) -> GraphQLField:
        return GraphQLField(
            type_=self.get_field_type(),
            args=self.get_field_arguments(),
            resolve=convert_field_ref_to_resolver(self.ref, many=self.many, name=self.name),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLOutputType:
        if is_pk_property(self.ref):
            return convert_model_field_to_graphql_output_type(self.owner.__model__._meta.pk)
        return convert_ref_to_graphql_output_type(self.ref, many=self.many, nullable=self.nullable)

    def get_field_arguments(self) -> GraphQLArgumentMap:
        arg_map = convert_field_ref_to_graphql_argument_map(self.ref, many=self.many)
        for arg in arg_map.values():
            arg.extensions[undine_settings.FIELD_EXTENSIONS_KEY] = self
        return arg_map

    def optimizer_hook(self, optimizer: QueryOptimizer) -> None:
        """Hook for customizing how field subclasses are optimized by the QueryOptimizer."""


class Filter:
    def __init__(
        self,
        ref: Any = None,
        *,
        lookup_expr: str = "exact",
        many: bool = False,
        distinct: bool = False,
        required: bool = False,
        alias_name: str | None = None,
        description: str | None = None,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a `GraphQLInputType` used for filtering a `ModelGQLType`.

        :param ref: Expression to filter by. Can be anything that `convert_to_filter_ref` can convert,
                    e.g., a string referencing a model field name, a `Q` expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `ModelGQLFilter` class.
        :param lookup_expr: Lookup expression to use for the filter.
        :param many: Whether the filter requires the input to be a list of values. If not provided,
                     looks at the lookup expression and tries to determine this from it.
        :param distinct: Whether the filter requires `queryset.distinct()` to be used.
        :param required: Whether the filter should be required.
        :param alias_name: If the reference is an expression or a subquery, this is the alias to use
                           for it in the queryset. If not provided, use the name of the attribute this
                           is assigned to in the `ModelGQLFilter` class.
        :param description: Description of the filter. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the filter is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the filter.
        """
        cache_signature(ref, depth=1)
        self.ref = convert_to_filter_ref(ref)
        self.lookup_expr = lookup_expr
        self.many = many or lookup_expr in ("in", "range")
        self.distinct = distinct
        self.required = required
        self.alias_name = alias_name
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.FILTER_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[ModelGQLFilter], name: str) -> None:
        self.owner = owner
        self.name = name

        if self.ref == "self":
            self.ref = owner

        if isinstance(self.ref, DeferredModelField):
            self.ref = self.ref.get_field(self.owner.__model__, self.ref.name or name)
            self.ref = convert_to_filter_ref(self.ref)

        if self.description is None:
            self.description = convert_ref_to_field_description(self.ref)

        # If the filter predicate is an expression or a subquery, it needs to be
        # aliased in a queryset so that it can be filtered with a value.
        # Use the 'alias_name' ans 'alias_value' attributes to do this.
        self.alias_name = self.alias_name or name
        self.alias_value: models.Expression | models.Subquery | None = None
        if isinstance(self.ref, models.Expression | models.Subquery):
            self.alias_value = self.ref

        self.filter_func = convert_filter_ref_to_filter_func(
            self.ref,
            lookup_expr=self.lookup_expr,
            name=self.alias_name,
        )

    def __call__(self, _ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Filter()"""
        cache_signature(_ref, depth=1)
        self.ref = convert_to_filter_ref(_ref)
        return self

    def get_expression(self, value: Any, info: GraphQLResolveInfo) -> models.Q:
        return self.filter_func(self.owner, info, value=value)

    def as_input_field(self) -> GraphQLInputField:
        return GraphQLInputField(
            type_=self.get_field_type(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLInputType:
        graphql_type = convert_ref_to_graphql_input_type(self.ref, model=self.owner.__model__)
        if self.many:
            graphql_type = GraphQLList(graphql_type)
        if self.required:
            graphql_type = GraphQLNonNull(graphql_type)
        return graphql_type


class Ordering:
    def __init__(
        self,
        ref: Any = None,
        *,
        null_order: Literal["first", "last"] | None = None,
        supports_reversing: bool = True,
        description: str | None = None,
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
        cache_signature(ref, depth=1)
        self.ref = convert_to_ordering_ref(ref)
        self.nulls_first = True if null_order == "first" else None
        self.nulls_last = True if null_order == "last" else None
        self.supports_reversing = supports_reversing
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.ORDER_BY_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[ModelGQLOrdering], name: str) -> None:
        self.owner = owner
        self.name = name

        if self.ref == "self":
            self.ref = owner

        if isinstance(self.ref, DeferredModelField):
            self.ref = self.ref.get_field(self.owner.__model__, self.ref.name or name)
            self.ref = convert_to_ordering_ref(self.ref)

        if self.description is None:
            self.description = convert_ref_to_field_description(self.ref)

        self.get_ordering = convert_ordering_ref_to_ordering_func(self.ref)

    def __call__(self, _ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Ordering()"""
        cache_signature(_ref, depth=1)
        self.ref = convert_to_ordering_ref(_ref)
        return self

    def get_expression(self, info: GraphQLResolveInfo, *, descending: bool = False) -> models.OrderBy:
        kwargs = {"nulls_first": self.nulls_first, "nulls_last": self.nulls_last, "descending": descending}
        return models.OrderBy(self.get_ordering(self.owner, info), **kwargs)


class Input:
    def __init__(
        self,
        ref: Any = None,
        *,
        many: bool = Undefined,
        required: bool = False,
        description: str | None = None,
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
        :param required: Whether the input should be required.
        :param description: Description for the input. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the input is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the input.
        """
        # TODO: Support non-model field inputs
        self.ref = convert_to_input_ref(ref)
        self.many = many
        self.required = required
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.INPUT_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[ModelGQLMutation], name: str) -> None:
        self.owner = owner
        self.name = name

        if self.ref == "self":
            self.ref = owner

        if isinstance(self.ref, DeferredModelField):
            self.ref = self.ref.get_field(self.owner.__model__, self.ref.name or name)
            self.ref = convert_to_input_ref(self.ref)

        if self.description is None:
            self.description = convert_ref_to_field_description(self.ref)
        if self.many is Undefined:
            self.many = is_field_ref_many(self.ref)

    def as_input_field(self, *, required: bool = False) -> GraphQLInputField:
        return GraphQLInputField(
            type_=self.get_field_type(required=required),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self, *, required: bool = False) -> GraphQLInputType:
        graphql_type = convert_ref_to_graphql_input_type(self.ref, model=self.owner.__model__)
        if required or self.required:
            graphql_type = GraphQLNonNull(graphql_type)
        if self.many:
            graphql_type = GraphQLNonNull(GraphQLList(graphql_type))
        return graphql_type
