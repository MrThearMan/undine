from __future__ import annotations

import functools
import itertools
import operator
import operator as op
from collections import defaultdict
from collections.abc import Iterable
from functools import reduce
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Self, Unpack

from django.db.models import Model, Q
from django.db.models.constants import LOOKUP_SEP
from graphql import DirectiveLocation, GraphQLInputField, GraphQLInputType, Undefined

from undine.converters import (
    convert_to_description,
    convert_to_filter_lookups,
    convert_to_filter_ref,
    convert_to_filter_resolver,
    convert_to_graphql_type,
)
from undine.dataclasses import FilterResults, LookupRef, MaybeManyOrNonNull
from undine.exceptions import (
    EmptyFilterResult,
    MismatchingModelError,
    MissingModelGenericError,
    NotCompatibleWithError,
    QueryTypeRequiresSingleModelError,
    UnionTypeModelsDifferentError,
    UnionTypeRequiresMultipleModelsError,
)
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.typing import ManyMatch, TModels
from undine.utils.graphql.type_registry import get_or_create_graphql_input_object_type
from undine.utils.graphql.utils import check_directives
from undine.utils.model_utils import get_model_field, get_model_fields_for_graphql, is_to_many, lookup_to_display_name
from undine.utils.reflection import (
    FunctionEqualityWrapper,
    cache_signature_if_function,
    get_members,
    get_wrapped_func,
    is_subclass,
)
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Container, Iterable

    from django.db.models import Model, QuerySet
    from graphql import GraphQLFieldResolver, GraphQLInputObjectType, GraphQLInputType

    from undine import QueryType, UnionType
    from undine.directives import Directive
    from undine.typing import (
        DjangoExpression,
        DjangoRequestProtocol,
        FilterAliasesFunc,
        FilterParams,
        FilterSetParams,
        GQLInfo,
        T,
        TModel,
        VisibilityFunc,
    )

__all__ = [
    "Filter",
    "FilterSet",
]


class FilterSetMeta(type):
    """A metaclass that modifies how a `FilterSet` is created."""

    # Set in '__new__'
    __models__: tuple[type[Model], ...]
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
            models = FilterSetMeta.__models__
            del FilterSetMeta.__models__
        except AttributeError as error:
            raise MissingModelGenericError(name=_name, cls="FilterSet") from error

        auto = kwargs.get("auto", undine_settings.AUTOGENERATION)
        exclude = set(kwargs.get("exclude", []))
        if auto:
            exclude |= set(_attrs)

            if len(models) == 1:
                _attrs |= get_filters_for_model(models[0], exclude=exclude)
            else:
                _attrs |= get_filters_for_models(models, exclude=exclude)

        filterset = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `Filter` names.
        filterset.__models__ = models
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

    def __getitem__(cls, models: type[type[TModel]] | tuple[type[TModel], ...]) -> type[FilterSet[*TModels]]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'FilterSet'!
        FilterSetMeta.__models__ = models if isinstance(models, tuple) else (models,)
        return cls  # type: ignore[return-value]

    def __call__(cls, ref: T) -> T:
        """
        Allow adding this FilterSet to a QueryType using a decorator syntax

        >>> class TaskFilterSet(FilterSet[Task]): ...
        >>>
        >>> @TaskFilterSet
        >>> class TaskType(QueryType[Task]): ...
        """
        from undine import QueryType, UnionType  # noqa: PLC0415

        if is_subclass(ref, QueryType):
            cls.__add_to_query_type__(ref)
        elif is_subclass(ref, UnionType):
            cls.__add_to_union_type__(ref)
        else:
            raise NotCompatibleWithError(obj=cls, other=ref)

        return ref

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
                    if not filter_value:
                        continue

                    results = cls.__build__(filter_value, info)
                    distinct |= results.distinct
                    aliases |= results.aliases
                    filter_count += results.filter_count
                    filters.extend(~frt for frt in results.filters)

                elif filter_name in {"AND", "OR", "XOR"}:
                    if not filter_value:
                        continue

                    results = cls.__build__(filter_value, info)
                    distinct |= results.distinct
                    aliases |= results.aliases
                    filter_count += results.filter_count
                    func = op.and_ if filter_name == "AND" else op.or_ if filter_name == "OR" else op.xor
                    filters.append(reduce(func, results.filters, Q()))

                else:
                    ftr = cls.__filter_map__[filter_name]
                    if filter_value in ftr.empty_values:
                        continue

                    distinct |= ftr.distinct
                    if ftr.aliases_func is not None:
                        aliases |= ftr.aliases_func(ftr, info, value=filter_value)

                    if ftr.many:
                        conditions = (ftr.get_expression(value, info) for value in filter_value)
                        filter_expression = reduce(ftr.match.operator, conditions, Q())
                    else:
                        filter_expression = ftr.get_expression(filter_value, info)

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
        return input_object_type  # noqa: RET504, RUF100

    def __input_fields__(cls) -> dict[str, GraphQLInputField]:
        """Defer creating fields until all QueryTypes have been registered."""
        return {frt.schema_name: frt.as_graphql_input_field() for frt in cls.__filter_map__.values()}

    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        """
        Determine if the given filterset is visible in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.
        """
        return True

    def __add_directive__(cls, directive: Directive, /) -> Self:
        """Add a directive to this `FilterSet`."""
        check_directives([directive], location=DirectiveLocation.INPUT_OBJECT)
        cls.__directives__.append(directive)
        return cls

    def __add_to_query_type__(cls, query_type: type[QueryType]) -> None:
        models = cls.__models__
        if len(models) != 1:
            raise QueryTypeRequiresSingleModelError(kind="FilterSet")

        if models[0] is not query_type.__model__:
            raise MismatchingModelError(
                name=cls.__name__,
                given_model=models[0],
                target=query_type.__name__,
                expected_model=query_type.__model__,
            )

        query_type.__filterset__ = cls  # type: ignore[assignment]

    def __add_to_union_type__(cls, union_type: type[UnionType]) -> None:
        models = cls.__models__
        if len(models) == 1:
            raise UnionTypeRequiresMultipleModelsError(kind="FilterSet")

        on_union_type = set(union_type.__query_types_by_model__)
        on_filterset = set(models)

        if on_union_type != on_filterset:
            raise UnionTypeModelsDifferentError(kind="FilterSet")

        union_type.__filterset__ = cls  # type: ignore[assignment]


class FilterSet(Generic[*TModels], metaclass=FilterSetMeta):
    """
    A class for adding filtering for a `QueryType`.

    Must set the Django Model this `FilterSet` is for using the generic type argument.
    Model must match the Model of the `QueryType` this `FilterSet` will be added to.

    The following parameters can be passed in the class definition:

    `auto: bool = <AUTOGENERATION setting>`
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
    __models__: ClassVar[tuple[type[Model], ...]]
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
    A class for defining a possible `FilterSet` input.
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
        :param empty_values: Values that will be ignored if they are provided as filter values.
        :param description: Description of the `Filter`.
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
        self.empty_values: Container = kwargs.get("empty_values", undine_settings.EMPTY_VALUES)
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.field_name: str = kwargs.get("field_name", Undefined)  # type: ignore[assignment]
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})

        check_directives(self.directives, location=DirectiveLocation.INPUT_FIELD_DEFINITION)
        self.extensions[undine_settings.FILTER_EXTENSIONS_KEY] = self

        self.aliases_func: FilterAliasesFunc | None = None
        self.visible_func: VisibilityFunc | None = None

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
        return convert_to_graphql_type(value, model=self.filterset.__models__[0], is_input=True)  # type: ignore[return-value]

    def aliases(self, func: FilterAliasesFunc | None = None, /) -> FilterAliasesFunc:
        """
        Decorate a function to add additional queryset aliases required by this Filter.

        >>> class TaskFilterSet(FilterSet[Task]):
        ...     name = Filter()
        ...
        ...     @name.aliases
        ...     def name_aliases(self: Filter, info: GQLInfo, *, value: str) -> dict[str, DjangoExpression]:
        ...         return {"foo": Value("bar")}
        """
        if func is None:  # Allow `@<filter_name>.aliases()`
            return self.aliases  # type: ignore[return-value]
        self.aliases_func = get_wrapped_func(func)
        return func

    def visible(self, func: VisibilityFunc | None = None, /) -> VisibilityFunc:
        """
        Decorate a function to change the Filter's visibility in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.

        >>> class TaskFilterSet(FilterSet[Task]):
        ...     name = Filter()
        ...
        ...     @name.visible
        ...     def name_visible(self: Filter, request: DjangoRequestProtocol) -> bool:
        ...         return False
        """
        if func is None:  # Allow `@<filter_name>.visible()`
            return self.visible  # type: ignore[return-value]
        self.visible_func = get_wrapped_func(func)
        return func

    def add_directive(self, directive: Directive, /) -> Self:
        """Add a directive to this filter."""
        check_directives([directive], location=DirectiveLocation.INPUT_FIELD_DEFINITION)
        self.directives.append(directive)
        return self


def get_filters_for_model(model: type[Model], *, exclude: Iterable[str] = ()) -> dict[str, Filter]:
    """Creates `Filters` for all the given Model's fields, except those in the 'exclude' list."""
    result: dict[str, Filter] = {}

    # Lookups are separated by '__', but auto-generated names use '_' instead.
    exclude = {"_".join(item.split(LOOKUP_SEP)) for item in exclude}

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


def get_filters_for_models(models: tuple[type[TModel], ...], *, exclude: Iterable[str] = ()) -> dict[str, Filter]:
    result: dict[str, Filter] = {}

    # Lookups are separated by '__', but auto-generated names use '_' instead.
    exclude = {"_".join(item.split(LOOKUP_SEP)) for item in exclude}

    fields_by_model: dict[type[Model], set[str]] = {}
    for model in models:
        fields: set[str] = set()

        for model_field in get_model_fields_for_graphql(model):
            field_name = model_field.name

            is_primary_key = bool(getattr(model_field, "primary_key", False))
            if is_primary_key:
                field_name = "pk"

            if field_name in exclude:
                continue

            fields.add(field_name)

        fields_by_model[model] = fields

    common_fields = functools.reduce(operator.and_, fields_by_model.values())

    graphql_types_by_model: dict[str, dict[type[Model], GraphQLInputType]] = defaultdict(dict)
    for model in fields_by_model:
        for field_name in common_fields:
            graphql_types_by_model[field_name][model] = convert_to_graphql_type(field_name, model=model, is_input=True)

    usable_fields: set[str] = set()
    for field_name, model_map in graphql_types_by_model.items():
        is_usable = all(field_1 == field_2 for field_1, field_2 in itertools.combinations(model_map.values(), 2))
        if is_usable:
            usable_fields.add(field_name)

    for field_name in usable_fields:
        model_field = get_model_field(model=models[0], lookup=field_name)

        lookups = sorted(convert_to_filter_lookups(model_field))  # type: ignore[arg-type]

        for lookup in lookups:
            # Filters for many-to-many relations should always use `qs.distinct()`
            distinct = is_to_many(model_field)

            display_name = lookup_to_display_name(lookup, model_field)

            name = f"{field_name}_{display_name}" if display_name else field_name
            if name in exclude:
                continue

            result[name] = Filter(field_name, lookup=lookup, distinct=distinct)

    return result
