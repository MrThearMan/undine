"""Code creating filters for a `QueryType`."""

from __future__ import annotations

import operator as op
from functools import reduce
from typing import TYPE_CHECKING, Any, Container, Iterable, Self

from django.db import models
from graphql import GraphQLInputField, GraphQLInputObjectType, GraphQLInputType, Undefined

from undine.converters import (
    convert_filter_ref_to_filter_resolver,
    convert_ref_to_graphql_input_type,
    convert_to_description,
    convert_to_filter_ref,
)
from undine.errors.exceptions import MissingModelError
from undine.settings import undine_settings
from undine.typing import CombinableExpression, FilterResults, GQLInfo
from undine.utils.decorators import cached_class_method
from undine.utils.graphql import maybe_list_or_non_null
from undine.utils.reflection import cache_signature_if_function, get_members
from undine.utils.text import dotpath, get_docstring, get_schema_name

if TYPE_CHECKING:
    from types import FunctionType


__all__ = [
    "Filter",
    "FilterSet",
]


class FilterSetMeta(type):
    """A metaclass that modifies how a `FilterSet` is created."""

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        *,
        model: type[models.Model] | None = None,
        auto_filters: bool = True,
        exclude: Iterable[str] = (),
        typename: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> FilterSetMeta:
        """See `FilterSet` for documentation of arguments."""
        if model is Undefined:  # Early return for the `FilterSet` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="FilterSet")

        if auto_filters:
            _attrs |= get_filters_for_model(model, exclude=set(exclude) | set(_attrs))

        # Add model to attrs before class creation so that it's available during `Filter.__set_name__`.
        _attrs["__model__"] = model
        instance: type[FilterSet] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible filter names.
        instance.__model__ = model
        instance.__filter_map__ = {get_schema_name(name): ftr for name, ftr in get_members(instance, Filter)}
        instance.__typename__ = typename or _name
        instance.__extensions__ = extensions or {} | {undine_settings.FILTER_INPUT_EXTENSIONS_KEY: instance}
        return instance


class FilterSet(metaclass=FilterSetMeta, model=Undefined):
    """
    Base class for creating a set of filters for a `QueryType`.
    Creates a single GraphQL InputObjectType from undine.Filters defined in the class,
    which can then be combined using logical operators.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `FilterSet` is for. This input is required.
               Must match the model of the `QueryType` this `FilterSet` is for.
    - `auto_filters`: Whether to add filters for all model fields and their lookups automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from the automatically added filters. No excludes by default.
    - `typename`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created `InputObjectType`. Defaults to `None`.

    >>> class MyFilters(FilterSet, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible filter names.

    @classmethod
    def __build__(cls, filter_data: dict[str, Any], info: GQLInfo) -> FilterResults:
        """
        Build a Q-object from the given filter data.
        Also indicate whether the filter should be distinct based on the fields in the filter data.

        :param filter_data: A map of filter schema names to input values.
        :param info: The GraphQL resolve info for the request.
        """
        filters: list[models.Q] = []
        distinct: bool = False
        aliases: dict[str, CombinableExpression] = {}

        for filter_name, filter_value in filter_data.items():
            if filter_name == "NOT":
                results = cls.__build__(filter_value, info)
                distinct = distinct or results.distinct
                aliases |= results.aliases
                filters.extend(~frt for frt in results.filters)

            elif filter_name in ("AND", "OR", "XOR"):
                results = cls.__build__(filter_value, info)
                distinct = distinct or results.distinct
                aliases |= results.aliases
                func = op.and_ if filter_name == "AND" else op.or_ if filter_name == "OR" else op.xor
                filters.append(reduce(func, results.filters))

            else:
                filter_ = cls.__filter_map__[filter_name]
                distinct = distinct or filter_.distinct
                filter_expression = filter_.get_expression(filter_value, info)
                if isinstance(filter_.ref, (models.Expression, models.Subquery)):
                    aliases[filter_.name] = filter_.ref

                filters.append(filter_expression)

        return FilterResults(filters=filters, distinct=distinct, aliases=aliases)

    @cached_class_method
    def __input_type__(cls) -> GraphQLInputObjectType:
        """
        Create a `GraphQLInputObjectType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """
        input_object_type = GraphQLInputObjectType(
            name=cls.__typename__,
            description=get_docstring(cls),
            fields={},
            extensions=cls.__extensions__,
        )

        def fields() -> dict[str, GraphQLInputField]:
            fields = {name: filter_.as_graphql_input() for name, filter_ in cls.__filter_map__.items()}
            input_field = GraphQLInputField(type_=input_object_type)
            fields["NOT"] = input_field
            fields["AND"] = input_field
            fields["OR"] = input_field
            fields["XOR"] = input_field
            return fields

        input_object_type._fields = fields
        return input_object_type


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
        A class representing a `GraphQLInputType` used for filtering a `QueryType`.

        :param ref: Expression to filter by. Can be anything that `convert_to_filter_ref` can convert:
                    a string referencing a model field name, an expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `FilterSet` class.
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
        self.lookup_expr = lookup_expr.lower()
        self.many = many or self.lookup_expr in undine_settings.LOOKUP_EXPRESSIONS_MANY
        self.distinct = distinct
        self.required = required
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.FILTER_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[FilterSet], name: str) -> None:
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

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref}, lookup_expr={self.lookup_expr!r})>"

    def get_expression(self, value: Any, info: GQLInfo) -> models.Q:
        return self.resolver(self.owner, info, value=value)

    def as_graphql_input(self) -> GraphQLInputField:
        return GraphQLInputField(
            type_=self.get_field_type(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLInputType:
        graphql_type = convert_ref_to_graphql_input_type(self.ref, model=self.owner.__model__, lookup=self.lookup_expr)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=self.required)


def get_filters_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Filter]:
    """Creates undine.Filters for all of the given model's non-related fields, except those in the 'exclude' list."""
    result: dict[str, Filter] = {}
    for model_field in model._meta._get_fields(reverse=False):
        if model_field.is_relation:
            continue

        field_name = model_field.name
        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if undine_settings.USE_PK_FIELD_NAME and is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        for lookup_expr in model_field.get_lookups():
            result[f"{field_name}_{lookup_expr}"] = Filter(field_name, lookup_expr=lookup_expr)

    return result
