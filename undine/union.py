from __future__ import annotations

import functools
import itertools
import operator
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Self, Unpack

from django.db.models import Model
from django.db.models.constants import LOOKUP_SEP
from graphql import DirectiveLocation, GraphQLInputField, Undefined

from undine.converters import (
    convert_to_description,
    convert_to_filter_lookups,
    convert_to_graphql_type,
    convert_to_union_filter_ref,
    convert_to_union_filter_resolver,
)
from undine.dataclasses import LookupRef, MaybeManyOrNonNull
from undine.exceptions import (
    GraphQLUnionResolveTypeInvalidValueError,
    GraphQLUnionResolveTypeModelNotFoundError,
    MissingModelGenericError,
    MissingUnionQueryTypeGenericError,
)
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.typing import ManyMatch, TModels, TQueryTypes
from undine.utils.graphql.type_registry import get_or_create_graphql_input_object_type, get_or_create_graphql_union
from undine.utils.graphql.utils import check_directives
from undine.utils.model_utils import get_model_field, get_model_fields_for_graphql, is_to_many, lookup_to_display_name
from undine.utils.reflection import FunctionEqualityWrapper, cache_signature_if_function, get_members, get_wrapped_func
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Container, Iterable

    from django.db.models import Q
    from graphql import (
        GraphQLAbstractType,
        GraphQLFieldResolver,
        GraphQLInputObjectType,
        GraphQLInputType,
        GraphQLUnionType,
    )

    from undine import GQLInfo, QueryType
    from undine.directives import Directive
    from undine.typing import (
        DjangoRequestProtocol,
        FilterAliasesFunc,
        FilterParams,
        FilterSetParams,
        TModel,
        TUnionType,
        UnionTypeParams,
        VisibilityFunc,
    )

__all__ = [
    "UnionFilter",
    "UnionFilterSet",
    "UnionType",
]


class UnionTypeMeta(type):
    """A metaclass that modifies how a `UnionType` is created."""

    # Set in '__new__'
    __query_types_by_model__: dict[type[Model], type[QueryType]]
    __schema_name__: str
    __filterset__: type[UnionFilterSet] | None
    __directives__: list[Directive]
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    # Internal use only
    __query_types__: Iterable[type[QueryType]]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[UnionTypeParams],
    ) -> UnionTypeMeta:
        if _name == "UnionType":  # Early return for the `UnionType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        try:
            query_types = UnionTypeMeta.__query_types__
            del UnionTypeMeta.__query_types__
        except AttributeError as error:
            raise MissingUnionQueryTypeGenericError(name=_name, cls="UnionType") from error

        union_type = super().__new__(cls, _name, _bases, _attrs)

        union_type.__query_types_by_model__ = {query_type.__model__: query_type for query_type in query_types}
        union_type.__schema_name__ = kwargs.get("schema_name", _name)
        union_type.__filterset__ = kwargs.get("filterset")
        union_type.__directives__ = kwargs.get("directives", [])
        union_type.__extensions__ = kwargs.get("extensions", {})
        union_type.__attribute_docstrings__ = parse_class_attribute_docstrings(union_type)

        check_directives(union_type.__directives__, location=DirectiveLocation.UNION)
        union_type.__extensions__[undine_settings.UNION_TYPE_EXTENSIONS_KEY] = union_type

        return union_type

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_union_type(cls.__union_type__())

    def __getitem__(cls, query_types: tuple[type[QueryType], ...]) -> type[UnionType[*TQueryTypes]]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'UnionType'!
        UnionTypeMeta.__query_types__ = query_types
        return cls  # type: ignore[return-value]

    def __resolve_type__(cls, value: Any, info: GQLInfo, abstract_type: GraphQLAbstractType) -> str:
        if not isinstance(value, Model):
            raise GraphQLUnionResolveTypeInvalidValueError(name=cls.__schema_name__, value=value)

        model = value.__class__
        query_type = cls.__query_types_by_model__.get(model)
        if query_type is None:
            raise GraphQLUnionResolveTypeModelNotFoundError(name=cls.__schema_name__, model=model)

        return query_type.__schema_name__

    def __union_type__(cls) -> GraphQLUnionType:
        return get_or_create_graphql_union(
            name=cls.__schema_name__,
            types=[query_type.__output_type__() for query_type in cls.__query_types_by_model__.values()],
            resolve_type=cls.__resolve_type__,
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )

    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        """
        Determine if the given union is visible in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.
        """
        return True

    def __add_directive__(cls, directive: Directive, /) -> Self:
        """Add a directive to this union."""
        check_directives([directive], location=DirectiveLocation.UNION)
        cls.__directives__.append(directive)
        return cls


class UnionType(Generic[*TQueryTypes], metaclass=UnionTypeMeta):
    """
    A class for creating a GraphQL Union based on two or more `QueryTypes`.

    Must set the `QueryTypes` this `UnionType` contains using the generic type argument.

    The following parameters can be passed in the class definition:

    `schema_name: str = <class name>`
        Override name for `UnionType` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `UnionType`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `UnionType`.

    >>> class TaskType(QueryType[Task]): ...
    >>> class ProjectType(QueryType[Project]): ...
    >>>
    >>> class Commentable(UnionType[TaskType, ProjectType]): ...
    """

    # Set in metaclass
    __query_types_by_model__: ClassVar[dict[type[Model], type[QueryType]]]
    __schema_name__: ClassVar[str]
    __filterset__: ClassVar[type[UnionFilterSet] | None]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    @classmethod
    def __process_results__(cls, instances: list[Any], info: GQLInfo) -> list[Any]:
        """Filter and order results of the union after everything has been fetched."""
        return instances


# Filtering


class UnionFilterSetMeta(type):
    """A metaclass that modifies how a `UnionFilterSet` is created."""

    # Set in '__new__'
    __models__: tuple[type[Model], ...]
    __filter_map__: dict[str, UnionFilter]
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
    ) -> UnionFilterSetMeta:
        if _name == "UnionFilterSet":  # Early return for the `UnionFilterSet` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        try:
            models = UnionFilterSetMeta.__models__
            del UnionFilterSetMeta.__models__
        except AttributeError as error:
            raise MissingModelGenericError(name=_name, cls="UnionFilterSet") from error

        auto = kwargs.get("auto", undine_settings.AUTOGENERATION)
        exclude = set(kwargs.get("exclude", []))
        if auto:
            exclude |= set(_attrs)
            _attrs |= get_filters_for_models(models, exclude=exclude)

        filterset = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `UnionFilter` names.
        filterset.__models__ = models
        filterset.__filter_map__ = get_members(filterset, UnionFilter)
        filterset.__schema_name__ = kwargs.get("schema_name", _name)
        filterset.__directives__ = kwargs.get("directives", [])
        filterset.__extensions__ = kwargs.get("extensions", {})
        filterset.__extensions__[undine_settings.FILTERSET_EXTENSIONS_KEY] = filterset
        filterset.__attribute_docstrings__ = parse_class_attribute_docstrings(filterset)

        check_directives(filterset.__directives__, location=DirectiveLocation.INPUT_OBJECT)

        for name, filter_ in filterset.__filter_map__.items():
            filter_.__connect__(filterset, name)  # type: ignore[arg-type]

        return filterset

    def __getitem__(cls, models: tuple[*TModels]) -> type[UnionFilterSet]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'UnionFilterSet'!
        UnionFilterSetMeta.__models__ = models
        return cls  # type: ignore[return-value]

    def __call__(cls, union_type: type[TUnionType]) -> type[TUnionType]:
        """
        Allow adding this UnionFilterSet to a UnionQueryType using a decorator syntax

        >>> class TaskType(QueryType[Task]): ...
        >>>
        >>> class ProjectType(QueryType[Project]): ...
        >>>
        >>> class CommentableFilterSet(UnionFilterSet[Task, Project]): ...
        >>>
        >>> @CommentableFilterSet
        >>> class CommentableType(UnionType[TaskType, ProjectType]): ...
        """
        union_type_models = set(union_type.__query_types_by_model__)
        filterset_models = set(cls.__models__)

        if filterset_models != union_type_models:
            msg = (
                f"UnionFilterSet '{cls.__name__}' models {filterset_models} do not match "
                f"UnionType '{union_type.__name__}' models {union_type_models}."
            )
            raise RuntimeError(msg)

        union_type.__filterset__ = cls  # type: ignore[assignment]
        return union_type

    def __input_type__(cls) -> GraphQLInputObjectType:
        """
        Create the input type to use for the `QueryType` this `UnionFilterSet` is for.

        The fields of the input object type are all the `UnionFilter` instances defined in this `UnionFilterSet`,
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
        """Add a directive to this `UnionFilterSet`."""
        check_directives([directive], location=DirectiveLocation.INPUT_OBJECT)
        cls.__directives__.append(directive)
        return cls


class UnionFilterSet(Generic[*TModels], metaclass=UnionFilterSetMeta):
    """
    A class for adding filtering for a `UnionType`.

    Must set the Django Model this `UnionFilterSet` is for using the generic type argument.
    Model must match the Model of the `UnionType` this `UnionFilterSet` will be added to.

    The following parameters can be passed in the class definition:

    `auto: bool = <AUTOGENERATION setting>`
        Whether to add `UnionFilter` attributes for all Model fields and their lookups automatically.

    `exclude: list[str] = []`
        Model fields to exclude from the automatically added `UnionFilter` attributes.

    `schema_name: str = <class name>`
        Override the name for the `InputObjectType` for this `UnionFilterSet` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `InputObjectType`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `InputObjectType`.

    >>> class TaskFilterSet(FilterSet[Task]): ...
    >>> class TaskQueryType(QueryType[Task], filterset=TaskFilterSet): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `Filter` names.

    # Set in metaclass
    __models__: tuple[type[Model], ...]
    __filter_map__: ClassVar[dict[str, UnionFilter]]
    __schema_name__: ClassVar[str]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]


class UnionFilter:
    """
    A class for defining a possible `UnionFilterSet` input.
    Represents an input field in the GraphQL `InputObjectType` for the `UnionFilterSet` this is added to.

    >>> class CommentableFilterSet(UnionFilterSet[Task, Project]):
    ...     name = UnionFilter()
    """

    def __init__(self, ref: Any = None, **kwargs: Unpack[FilterParams]) -> None:
        """
        Create a new `UnionFilter`.

        :param ref: The expression to filter by. Must be convertable by the `convert_to_filter_ref` function.
                    If not provided, use the name of the attribute this is assigned to in the `UnionFilterSet` class.
        :param lookup: The lookup expression to use for the `UnionFilter`.
        :param many: If `True`, the `UnionFilter` will accept a list of values, and filtering will be done by matching
                     all the provided values against the filter condition.
        :param match: Sets the behavior of `many` so that the filter condition will include an item if it
                      matches either "any", "all", or "one_of" of the provided values.
        :param distinct: Does the `UnionFilter` require `queryset.distinct()` to be used?
        :param required: Is the `UnionFilter` is a required input?
        :param empty_values: Values that will be ignored if they are provided as filter values.
        :param description: Description of the `UnionFilter`.
        :param deprecation_reason: If the `UnionFilter` is deprecated, describes the reason for deprecation.
        :param field_name: Name of the field in the Django model. If not provided, use the name of the attribute.
        :param schema_name: Actual name of the `UnionFilter` in the GraphQL schema.
                            Can be used to alias the `UnionFilter` for the schema,
                            or when the desired name is a Python keyword (e.g. `if` or `from`).
        :param directives: GraphQL directives for the `UnionFilter`.
        :param extensions: GraphQL extensions for the `UnionFilter`.
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

    def __connect__(self, filterset: type[UnionFilterSet], name: str) -> None:
        """Connect this `UnionFilter` to the given `UnionFilterSet` using the given name."""
        self.filterset = filterset
        self.name = name
        self.field_name = self.field_name or name
        self.schema_name = self.schema_name or to_schema_name(name)

        if isinstance(self.ref, str):
            self.field_name = self.ref

        self.ref = convert_to_union_filter_ref(self.ref, caller=self)

        if self.description is Undefined:
            self.description = self.filterset.__attribute_docstrings__.get(name)
            if self.description is None:
                self.description = convert_to_description(self.ref)

        self.resolver = convert_to_union_filter_resolver(self.ref, caller=self)

    def __call__(self, ref: GraphQLFieldResolver, /) -> UnionFilter:
        """Called when using as decorator with parenthesis: @UnionFilter()"""
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
        Decorate a function to add additional queryset aliases required by this UnionFilter.

        >>> class TaskFilterSet(UnionFilterSet[Task, Project]):
        ...     name = UnionFilter()
        ...
        ...     @name.aliases
        ...     def name_aliases(self: UnionFilter, info: GQLInfo, *, value: str) -> dict[str, DjangoExpression]:
        ...         return {"foo": Value("bar")}
        """
        if func is None:  # Allow `@<filter_name>.aliases()`
            return self.aliases  # type: ignore[return-value]
        self.aliases_func = get_wrapped_func(func)
        return func

    def visible(self, func: VisibilityFunc | None = None, /) -> VisibilityFunc:
        """
        Decorate a function to change the UnionFilter's visibility in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.

        >>> class TaskFilterSet(UnionFilterSet[Task, Project]):
        ...     name = UnionFilter()
        ...
        ...     @name.visible
        ...     def name_visible(self: UnionFilter, request: DjangoRequestProtocol) -> bool:
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


def get_filters_for_models(models: tuple[type[TModel], ...], *, exclude: Iterable[str] = ()) -> dict[str, UnionFilter]:
    result: dict[str, UnionFilter] = {}

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

            result[name] = UnionFilter(field_name, lookup=lookup, distinct=distinct)

    return result
