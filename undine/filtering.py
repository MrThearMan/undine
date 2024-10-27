"""Contains code for creating filtering options for a `QueryType`."""

from __future__ import annotations

import operator as op
from functools import reduce
from typing import TYPE_CHECKING, Any, Container, Iterable, Self

from django.db import models
from graphql import GraphQLInputField, GraphQLInputType, Undefined

from undine.converters import convert_filter_ref_to_filter_resolver, convert_to_filter_ref, convert_to_graphql_type
from undine.errors.exceptions import MissingModelError
from undine.parsers import parse_description
from undine.settings import undine_settings
from undine.typing import CombinableExpression, FilterResults, GQLInfo, LookupRef
from undine.utils.graphql import get_or_create_input_object_type, maybe_list_or_non_null
from undine.utils.model_utils import get_lookup_field_name
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members
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
        auto: bool = True,
        exclude: Iterable[str] = (),
        typename: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> FilterSetMeta:
        """See `FilterSet` for documentation of arguments."""
        if model is Undefined:  # Early return for the `FilterSet` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="FilterSet")

        if auto:
            _attrs |= get_filters_for_model(model, exclude=set(exclude) | set(_attrs))

        # Add to attrs things that need to be available during `Filter.__set_name__`.
        _attrs["__model__"] = model
        instance: type[FilterSet] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use `__dunder__` names to avoid name collisions with possible `undine.Filter` names.
        instance.__model__ = model
        instance.__filter_map__ = {get_schema_name(name): ftr for name, ftr in get_members(instance, Filter)}
        instance.__typename__ = typename or _name
        instance.__extensions__ = (extensions or {}) | {undine_settings.FILTERSET_EXTENSIONS_KEY: instance}
        return instance


class FilterSet(metaclass=FilterSetMeta, model=Undefined):
    """
    A class representing a `GraphQLInputObjectType` used for filtering a `QueryType`.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `FilterSet` is for. This input is required.
               Must match the model of the `QueryType` this `FilterSet` is for.
    - `auto`: Whether to add undine.Filter fields for all model fields and their lookups automatically.
              Defaults to `True`.
    - `exclude`: List of model fields to exclude from the automatically added filters. No excludes by default.
    - `typename`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created `InputObjectType`. Defaults to `None`.

    >>> class MyFilters(FilterSet, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `undine.Filter` names.

    @classmethod
    def __build__(cls, filter_data: dict[str, Any], info: GQLInfo) -> FilterResults:
        """
        Build a list of 'models.Q' expression from the given filter data to apply to the queryset.
        Also indicate if 'queryset.distinct()' is needed, and what aliases required.

        :param filter_data: The data to build filters from.
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

            elif filter_name in {"AND", "OR", "XOR"}:
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

    @classmethod
    def __input_type__(cls) -> GraphQLInputType:
        """
        Create a `GraphQLInputObjectType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """

        # Defer creating fields so that logical filters can be added.
        def fields() -> dict[str, GraphQLInputField]:
            fields = {name: frt.as_graphql_input() for name, frt in cls.__filter_map__.items()}
            input_field = GraphQLInputField(type_=input_object_type)
            fields["NOT"] = input_field
            fields["AND"] = input_field
            fields["OR"] = input_field
            fields["XOR"] = input_field
            return fields

        # Assign to a variable so that `fields()` above can access it.
        input_object_type = get_or_create_input_object_type(
            name=cls.__typename__,
            description=get_docstring(cls),
            fields=FunctionEqualityWrapper(fields, context=cls),
            extensions=cls.__extensions__,
        )
        return input_object_type  # noqa: RET504


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
        :param many: Whether the Filter requires the input to be a list of values. If not provided,
                     looks at the lookup expression and tries to determine this from it.
        :param distinct: Whether the Filter requires `queryset.distinct()` to be used.
        :param required: Whether the Filter is a required input.
        :param description: Description of the Filter. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If the Filter is deprecated, describes the reason for deprecation.
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
            self.description = parse_description(self.ref)

        self.resolver = convert_filter_ref_to_filter_resolver(self.ref, caller=self)

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
        lookup = LookupRef(ref=self.ref, lookup=self.lookup_expr)
        graphql_type = convert_to_graphql_type(lookup, model=self.owner.__model__, is_input=True)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=self.required)


def get_filters_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Filter]:
    """Creates undine.Filters for all of the given model's non-related fields, except those in the 'exclude' list."""
    result: dict[str, Filter] = {}
    for model_field in model._meta._get_fields(reverse=False):
        if model_field.is_relation:
            continue

        field_name = model_field.name
        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if is_primary_key:
            field_name = get_lookup_field_name(model)

        if field_name in exclude:
            continue

        for lookup_expr in model_field.get_lookups():
            result[f"{field_name}_{lookup_expr}"] = Filter(field_name, lookup_expr=lookup_expr)

    return result
