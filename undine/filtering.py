from __future__ import annotations

import operator as op
from functools import reduce
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Unpack

from django.db.models import Q
from graphql import DirectiveLocation, GraphQLInputField, Undefined

from undine.converters import (
    convert_to_description,
    convert_to_filter_lookups,
    convert_to_filter_ref,
    convert_to_filter_resolver,
    convert_to_graphql_type,
)
from undine.dataclasses import FilterResults, LookupRef, MaybeManyOrNonNull
from undine.exceptions import EmptyFilterResult, MissingModelGenericError
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.typing import Annotatable, ManyMatch, TModel
from undine.utils.graphql.type_registry import get_or_create_graphql_input_object_type
from undine.utils.graphql.utils import check_directives
from undine.utils.model_utils import get_model_fields_for_graphql, is_to_many, lookup_to_display_name
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Container

    from django.db.models import Model, QuerySet
    from graphql import GraphQLFieldResolver, GraphQLInputObjectType, GraphQLInputType

    from undine.directives import Directive
    from undine.typing import DjangoExpression, FilterParams, FilterSetParams, GQLInfo

__all__ = [
    "Filter",
    "FilterSet",
]


class FilterSetMeta(type):
    """A metaclass that modifies how a `FilterSet` is created."""

    # Set in '__new__'
    __model__: type[Model]
    __filter_map__: dict[str, Filter]
    __schema_name__: str
    __directives__: list[Directive]
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[FilterSetParams],
    ) -> FilterSetMeta:
        if _name == "FilterSet":  # Early return for the `FilterSet` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        try:
            model = FilterSetMeta.__model__
            del FilterSetMeta.__model__
        except AttributeError as error:
            raise MissingModelGenericError(name=_name, cls="FilterSet") from error

        auto = kwargs.get("auto", True)
        exclude = set(kwargs.get("exclude", []))
        if auto:
            exclude |= set(_attrs)
            _attrs |= get_filters_for_model(model, exclude=exclude)

        filterset = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `Filter` names.
        filterset.__model__ = model
        filterset.__filter_map__ = get_members(filterset, Filter)
        filterset.__schema_name__ = kwargs.get("schema_name", _name)
        filterset.__directives__ = kwargs.get("directives", [])
        filterset.__extensions__ = kwargs.get("extensions", {})
        filterset.__extensions__[undine_settings.FILTERSET_EXTENSIONS_KEY] = filterset
        filterset.__attribute_docstrings__ = parse_class_attribute_docstrings(filterset)

        check_directives(filterset.__directives__, location=DirectiveLocation.INPUT_OBJECT)

        for name, filter_ in filterset.__filter_map__.items():
            filter_.__connect__(filterset, name)  # type: ignore[arg-type]

        return filterset

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_input_object_type(cls.__input_type__())

    def __getitem__(cls, model: type[TModel]) -> type[FilterSet[TModel]]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'FilterSet'!
        FilterSetMeta.__model__ = model
        return cls  # type: ignore[return-value]

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
        aliases: dict[str, DjangoExpression] = {}
        none: bool = False
        filter_count: int = 0

        try:
            for filter_name, filter_value in filter_data.items():
                if filter_name == "NOT":
                    results = cls.__build__(filter_value, info)
                    distinct |= results.distinct
                    aliases |= results.aliases
                    filter_count += results.filter_count
                    filters.extend(~frt for frt in results.filters)

                elif filter_name in {"AND", "OR", "XOR"}:
                    results = cls.__build__(filter_value, info)
                    distinct |= results.distinct
                    aliases |= results.aliases
                    filter_count += results.filter_count
                    func = op.and_ if filter_name == "AND" else op.or_ if filter_name == "OR" else op.xor
                    filters.append(reduce(func, results.filters, Q()))

                else:
                    frt = cls.__filter_map__[filter_name]
                    distinct |= frt.distinct
                    aliases |= frt.required_aliases
                    if isinstance(frt.ref, Annotatable):
                        aliases[frt.name] = frt.ref

                    if frt.many:
                        conditions = (frt.get_expression(value, info) for value in filter_value)
                        filter_expression = reduce(frt.match.operator, conditions, Q())
                    else:
                        filter_expression = frt.get_expression(filter_value, info)

                    filters.append(filter_expression)
                    filter_count += 1

        except EmptyFilterResult:
            none = True

        return FilterResults(filters=filters, aliases=aliases, distinct=distinct, none=none, filter_count=filter_count)

    def __input_type__(cls) -> GraphQLInputObjectType:
        """
        Create the input type to use for the `QueryType` this `FilterSet` is for.

        The fields of the input object type are all the `Filter` instances defined in this `FilterSet`,
        as well as a few special fields (NOT, AND, OR, XOR) for logical operations.
        """

        # Defer creating fields so that logical filters can be added.
        def fields() -> dict[str, GraphQLInputField]:
            inputs = cls.__input_fields__()
            input_field = GraphQLInputField(type_=input_object_type)
            inputs["NOT"] = input_field
            inputs["AND"] = input_field
            inputs["OR"] = input_field
            inputs["XOR"] = input_field
            return inputs

        # Assign to a variable so that `fields()` above can access it.
        input_object_type = get_or_create_graphql_input_object_type(
            name=cls.__schema_name__,
            description=get_docstring(cls),
            fields=FunctionEqualityWrapper(fields, context=cls),
            extensions=cls.__extensions__,
        )
        return input_object_type  # noqa: RET504

    def __input_fields__(cls) -> dict[str, GraphQLInputField]:
        """Defer creating fields until all QueryTypes have been registered."""
        return {frt.schema_name: frt.as_graphql_input_field() for frt in cls.__filter_map__.values()}


class FilterSet(Generic[TModel], metaclass=FilterSetMeta):
    """
    A class for adding filtering for a `QueryType`.

    Must set the Django Model this `FilterSet` is for using the generic type argument.
    Model must match the Model of the `QueryType` this `FilterSet` will be added to.

    The following parameters can be passed in the class definition:

    `auto: bool = True`
        Whether to add `Filter` attributes for all Model fields and their lookups automatically.

    `exclude: list[str] = []`
        Model fields to exclude from the automatically added `Filter` attributes.

    `schema_name: str = <class name>`
        Override the name for the `InputObjectType` for this `FilterSet` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `InputObjectType`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `InputObjectType`.

    >>> class TaskFilterSet(FilterSet[Task]): ...
    >>> class TaskQueryType(QueryType[Task], filterset=TaskFilterSet): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `Filter` names.

    # Set in metaclass
    __model__: ClassVar[type[Model]]
    __filter_map__: ClassVar[dict[str, Filter]]
    __schema_name__: ClassVar[str]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        """Filtering that should be done to the queryset after all other filters have been applied."""
        return queryset  # pragma: no cover


class Filter:
    """
    A class for defining a possible filter input.
    Represents an input field in the GraphQL `InputObjectType` for the `FilterSet` this is added to.

    >>> class TaskFilterSet(FilterSet[Task]):
    ...     name = Filter()
    """

    def __init__(self, ref: Any = None, **kwargs: Unpack[FilterParams]) -> None:
        """
        Create a new `Filter`.

        :param ref: The expression to filter by. Must be convertable by the `convert_to_filter_ref` function.
                    If not provided, use the name of the attribute this is assigned to in the `FilterSet` class.
        :param lookup: The lookup expression to use for the `Filter`.
        :param many: If `True`, the `Filter` will accept a list of values, and filtering will be done by matching
                     all the provided values against the filter condition.
        :param match: Sets the behavior of `many` so that the filter condition will include an item if it
                      matches either "any", "all", or "one_of" of the provided values.
        :param distinct: Does the `Filter` require `queryset.distinct()` to be used?
        :param required: Is the `Filter` is a required input?
        :param description: Description of the `Filter`.
        :param required_aliases: `QuerySet` aliases required for this `Filter`.
        :param deprecation_reason: If the `Filter` is deprecated, describes the reason for deprecation.
        :param field_name: Name of the field in the Django model. If not provided, use the name of the attribute.
        :param schema_name: Actual name of the `Filter` in the GraphQL schema. Can be used to alias the `Filter`
                            for the schema, or when the desired name is a Python keyword (e.g. `if` or `from`).
        :param directives: GraphQL directives for the `Filter`.
        :param extensions: GraphQL extensions for the `Filter`.
        """
        self.ref: Any = cache_signature_if_function(ref, depth=1)

        self.lookup: str = kwargs.get("lookup", "exact")
        self.many: bool = kwargs.get("many", False)
        self.match: ManyMatch = ManyMatch(kwargs.get("match", ManyMatch.any))
        self.distinct: bool = kwargs.get("distinct", False)
        self.required: bool = kwargs.get("required", False)
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.required_aliases: dict[str, DjangoExpression] = kwargs.get("required_aliases", {})
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.field_name: str = kwargs.get("field_name", Undefined)  # type: ignore[assignment]
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})

        check_directives(self.directives, location=DirectiveLocation.INPUT_FIELD_DEFINITION)
        self.extensions[undine_settings.FILTER_EXTENSIONS_KEY] = self

    def __connect__(self, filterset: type[FilterSet], name: str) -> None:
        """Connect this `Filter` to the given `FilterSet` using the given name."""
        self.filterset = filterset
        self.name = name
        self.field_name = self.field_name or name
        self.schema_name = self.schema_name or to_schema_name(name)

        if isinstance(self.ref, str):
            self.field_name = self.ref

        self.ref = convert_to_filter_ref(self.ref, caller=self)

        if self.description is Undefined:
            self.description = self.filterset.__attribute_docstrings__.get(name)
            if self.description is None:
                self.description = convert_to_description(self.ref)

        self.resolver = convert_to_filter_resolver(self.ref, caller=self)

    def __call__(self, ref: GraphQLFieldResolver, /) -> Filter:
        """Called when using as decorator with parenthesis: @Filter()"""
        self.ref = cache_signature_if_function(ref, depth=1)
        return self

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref!r}, lookup={self.lookup!r})>"

    def __str__(self) -> str:
        inpt = self.as_graphql_input_field()
        return undine_settings.SDL_PRINTER.print_input_field(self.schema_name, inpt, indent=False)

    def get_expression(self, value: Any, info: GQLInfo) -> Q:
        return self.resolver(self, info, value=value)

    def as_graphql_input_field(self) -> GraphQLInputField:
        return GraphQLInputField(
            type_=self.get_field_type(),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            out_name=self.name,
            extensions=self.extensions,
        )

    def get_field_type(self) -> GraphQLInputType:
        lookup = LookupRef(ref=self.ref, lookup=self.lookup)
        value = MaybeManyOrNonNull(lookup, many=self.many, nullable=not self.required)
        return convert_to_graphql_type(value, model=self.filterset.__model__, is_input=True)  # type: ignore[return-value]


def get_filters_for_model(model: type[Model], *, exclude: Container[str] = ()) -> dict[str, Filter]:
    """Creates `Filters` for all the given Model's fields, except those in the 'exclude' list."""
    result: dict[str, Filter] = {}

    for model_field in get_model_fields_for_graphql(model):
        field_name = model_field.name

        # Filters for many-to-many relations should always use `qs.distinct()`
        distinct = is_to_many(model_field)

        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        lookups = sorted(convert_to_filter_lookups(model_field))  # type: ignore[arg-type]

        for lookup in lookups:
            display_name = lookup_to_display_name(lookup, model_field)

            name = f"{field_name}_{display_name}" if display_name else field_name
            if name in exclude:
                continue

            result[name] = Filter(field_name, lookup=lookup, distinct=distinct)

    return result
