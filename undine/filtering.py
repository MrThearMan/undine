from __future__ import annotations

import operator as op
from functools import reduce
from typing import TYPE_CHECKING, Any, Literal, Self

from django.db.models import Expression, Q, QuerySet, Subquery
from graphql import GraphQLInputField, GraphQLInputType, Undefined

from undine.converters import convert_filter_ref_to_filter_resolver, convert_to_filter_ref, convert_to_graphql_type
from undine.dataclasses import FilterResults, LookupRef
from undine.errors.exceptions import EmptyFilterResult, MissingModelError
from undine.parsers import parse_class_variable_docstrings, parse_description
from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_input_object_type, maybe_list_or_non_null
from undine.utils.model_utils import get_model_fields_for_graphql
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Container, Iterable
    from types import FunctionType

    from django.db.models import Model

    from undine.typing import ExpressionLike, GQLInfo


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
        # See `FilterSet` for documentation of arguments.
        model: type[Model] | None = None,
        auto: bool = True,
        exclude: Iterable[str] = (),
        typename: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> FilterSetMeta:
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
        instance.__filter_map__ = get_members(instance, Filter)
        instance.__typename__ = typename or _name
        instance.__extensions__ = (extensions or {}) | {undine_settings.FILTERSET_EXTENSIONS_KEY: instance}
        return instance


class FilterSet(metaclass=FilterSetMeta, model=Undefined):
    """
    A class for adding filtering for a QueryType.
    Represents a GraphQL `InputObjectType` in the GraphQL schema.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django `Model` this `FilterSet` is for. This input is required.
               Must match the `Model` of the `QueryType` this `FilterSet` will be added to.
    - `auto`: Whether to add `undine.Filter` fields for all `Model` fields and their lookups automatically.
              Defaults to `True`.
    - `exclude`: List of `Model` fields to exclude from the automatically added filters. No excludes by default.
    - `typename`: Override the name for the `InputObjectType` in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created `InputObjectType`.

    >>> class MyFilters(FilterSet, model=...): ...
    >>> class MyQueryType(QueryType, model=..., filterset=MyFilters): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `undine.Filter` names.

    @classmethod
    def __build__(cls, filter_data: dict[str, Any], info: GQLInfo) -> FilterResults:
        """
        Build a list of 'Q' expression from the given filter data to apply to the queryset.
        Also indicate if 'queryset.distinct()' is needed, what aliases are required,
        or if the filtering should result in an empty queryset.

        :param filter_data: The input filter data.
        :param info: The GraphQL resolve info for the request.
        """
        filters: list[Q] = []
        distinct: bool = False
        aliases: dict[str, ExpressionLike] = {}
        none: bool = False

        try:
            for filter_name, filter_value in filter_data.items():
                if filter_name == "NOT":
                    results = cls.__build__(filter_value, info)
                    distinct |= results.distinct
                    aliases |= results.aliases
                    filters.extend(~frt for frt in results.filters)

                elif filter_name in {"AND", "OR", "XOR"}:
                    results = cls.__build__(filter_value, info)
                    distinct |= results.distinct
                    aliases |= results.aliases
                    func = op.and_ if filter_name == "AND" else op.or_ if filter_name == "OR" else op.xor
                    filters.append(reduce(func, results.filters, Q()))

                else:
                    frt = cls.__filter_map__[filter_name]
                    distinct |= frt.distinct
                    aliases |= frt.required_aliases
                    if isinstance(frt.ref, (Expression, Subquery)):
                        aliases[frt.name] = frt.ref

                    if frt.many:
                        func = op.and_ if frt.match == "all" else op.or_
                        conditions = (frt.get_expression(value, info) for value in filter_value)
                        filter_expression = reduce(func, conditions, Q())
                    else:
                        filter_expression = frt.get_expression(filter_value, info)

                    filters.append(filter_expression)

        except EmptyFilterResult:
            none = True

        return FilterResults(filters=filters, aliases=aliases, distinct=distinct, none=none)

    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        """Filtering that should be done to the queryset after all other filters have been applied."""
        return queryset

    @classmethod
    def __input_type__(cls) -> GraphQLInputType:
        """
        Create the input type to use for the `QueryType` this `FilterSet` is for.

        The input is a nullable GraphQL `InputObjectType` whose fields are
        all the `undine.Filter` instances defined in this `FilterSet`,
        as well as a few special fields (NOT, AND, OR, XOR) for logical operations.
        """

        # Defer creating fields so that logical filters can be added.
        def fields() -> dict[str, GraphQLInputField]:
            inputs = {to_schema_name(name): frt.as_graphql_input() for name, frt in cls.__filter_map__.items()}
            input_field = GraphQLInputField(type_=input_object_type)
            inputs["NOT"] = input_field
            inputs["AND"] = input_field
            inputs["OR"] = input_field
            inputs["XOR"] = input_field
            return inputs

        # Assign to a variable so that `fields()` above can access it.
        input_object_type = get_or_create_input_object_type(
            name=cls.__typename__,
            description=get_docstring(cls),
            fields=FunctionEqualityWrapper(fields, context=cls),
            extensions=cls.__extensions__,
        )
        return input_object_type  # noqa: RET504


class Filter:
    """
    A class for defining a possible filter input.
    Represents a field in the GraphQL `InputObjectType` for the `FilterSet` this is added to.

    >>> class MyFilters(FilterSet, model=...):
    ...     filter_name = Filter()
    """

    def __init__(  # noqa: PLR0913
        self,
        ref: Any = None,
        *,
        lookup: str = "exact",
        many: bool = False,
        match: Literal["any", "all"] = "any",
        distinct: bool = False,
        required: bool = False,
        description: str | None = Undefined,
        model_field_name: str | None = None,
        required_aliases: dict[str, ExpressionLike] | None = None,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        Create a new `Filter`.

        :param ref: The expression to filter by. Must be convertable by the `convert_to_filter_ref` function.
                    If not provided, use the name of the attribute this is assigned to in the `FilterSet` class.
        :param lookup: The lookup expression to use for the `Filter`.
        :param many: If `True`, the `Filter` will accept a list of values, and filtering will be done by matching
                     all the provided values against the filter condition.
        :param match: Sets the behavior of `many` so that the filter condition will include an item if it
                      matches either "any" or "all" of the provided values.
        :param distinct: Does the `Filter` require `queryset.distinct()` to be used?
        :param required: Is the `Filter` is a required input?
        :param description: Description of the `Filter`.
        :param model_field_name: Name of the `Model` field this `Filter` is for if different from
                                 its name on the `FilterSet`.
        :param required_aliases: `QuerySet` aliases required for this `Filter`.
        :param deprecation_reason: If the `Filter` is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the `Filter`.
        """
        self.ref = cache_signature_if_function(ref, depth=1)
        self.lookup = lookup.lower()
        self.many = many
        self.match = match
        self.distinct = distinct
        self.required = required
        self.description = description
        self.model_field_name = model_field_name
        self.required_aliases = required_aliases or {}
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.FILTER_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[FilterSet], name: str) -> None:
        # Called as part of the descriptor protocol if this `Filter` is assigned
        # to a variable in the class body of a `FilterSet`.
        self.filterset = owner
        self.name = name

        if self.model_field_name is None:
            self.model_field_name = self.ref if isinstance(self.ref, str) else self.name

        self.ref = convert_to_filter_ref(self.ref, caller=self)

        if self.description is Undefined:
            variable_docstrings = parse_class_variable_docstrings(self.filterset)
            self.description = variable_docstrings.get(self.name, Undefined)
            if self.description is Undefined:
                self.description = parse_description(self.ref)

        self.resolver = convert_filter_ref_to_filter_resolver(self.ref, caller=self)

    def __call__(self, ref: FunctionType, /) -> Self:
        """Called when using as decorator with parenthesis: @Filter()"""
        self.ref = cache_signature_if_function(ref, depth=1)
        return self

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref}, lookup={self.lookup!r})>"

    def get_expression(self, value: Any, info: GQLInfo) -> Q:
        return self.resolver(self, info, value=value)

    def as_graphql_input(self) -> GraphQLInputField:
        return GraphQLInputField(
            type_=self.get_field_type(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            out_name=self.name,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLInputType:
        lookup = LookupRef(ref=self.ref, lookup=self.lookup)
        graphql_type = convert_to_graphql_type(lookup, model=self.filterset.__model__, is_input=True)
        return maybe_list_or_non_null(graphql_type, many=self.many, required=self.required)


def get_filters_for_model(model: type[Model], *, exclude: Container[str]) -> dict[str, Filter]:  # TODO: Test
    """Creates undine.Filters for all the given Model's non-related fields, except those in the 'exclude' list."""
    result: dict[str, Filter] = {}
    for model_field in get_model_fields_for_graphql(model, include_relations=False):
        field_name = model_field.name

        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        for lookup in model_field.get_lookups():
            name = f"{field_name}_{lookup}"
            if name in exclude:
                continue

            # TODO: Filter out fields that don't make sense for filtering (e.g. FileFields or nonsensical lookups)

            result[name] = Filter(field_name, lookup=lookup)

    return result
