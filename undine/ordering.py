from __future__ import annotations

import functools
import itertools
import operator
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Self, Unpack

from django.db.models import OrderBy
from graphql import DirectiveLocation, GraphQLEnumValue, Undefined

from undine.converters import convert_to_description, convert_to_graphql_type, convert_to_order_ref
from undine.dataclasses import OrderResults
from undine.exceptions import (
    GraphQLInvalidOrderDataError,
    MismatchingModelError,
    MissingModelGenericError,
    NotCompatibleWithError,
    QueryTypeRequiresSingleModelError,
    UnionTypeModelsDifferentError,
    UnionTypeRequiresMultipleModelsError,
)
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.typing import TModels
from undine.utils.graphql.type_registry import get_or_create_graphql_enum
from undine.utils.graphql.utils import check_directives
from undine.utils.model_utils import get_model_field, get_model_fields_for_graphql
from undine.utils.reflection import get_members, get_wrapped_func, is_subclass
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models import Model
    from graphql import GraphQLEnumType, GraphQLInputType

    from undine import QueryType, UnionType
    from undine.directives import Directive
    from undine.typing import (
        DjangoExpression,
        DjangoRequestProtocol,
        GQLInfo,
        OrderAliasesFunc,
        OrderParams,
        OrderSetParams,
        T,
        TModel,
        VisibilityFunc,
    )

__all__ = [
    "Order",
    "OrderSet",
]


class OrderSetMeta(type):
    """A metaclass that modifies how an `OrderSet` is created."""

    # Set in '__new__'
    __models__: tuple[type[Model], ...]
    __order_map__: dict[str, Order]
    __schema_name__: str
    __directives__: list[Directive]
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[OrderSetParams],
    ) -> OrderSetMeta:
        if _name == "OrderSet":  # Early return for the `OrderSet` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        try:
            models = OrderSetMeta.__models__
            del OrderSetMeta.__models__
        except AttributeError as error:
            raise MissingModelGenericError(name=_name, cls="OrderSet") from error

        auto = kwargs.get("auto", undine_settings.AUTOGENERATION)
        exclude = set(kwargs.get("exclude", []))
        if auto:
            exclude |= set(_attrs)

            if len(models) == 1:
                _attrs |= get_orders_for_model(models[0], exclude=exclude)
            else:
                _attrs |= get_orders_for_models(models, exclude=exclude)

        orderset = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `Order` names.
        orderset.__models__ = models
        orderset.__order_map__ = get_members(orderset, Order)
        orderset.__schema_name__ = kwargs.get("schema_name", _name)
        orderset.__directives__ = kwargs.get("directives", [])
        orderset.__extensions__ = kwargs.get("extensions", {})
        orderset.__attribute_docstrings__ = parse_class_attribute_docstrings(orderset)

        check_directives(orderset.__directives__, location=DirectiveLocation.ENUM)
        orderset.__extensions__[undine_settings.ORDERSET_EXTENSIONS_KEY] = orderset

        for name, order in orderset.__order_map__.items():
            order.__connect__(orderset, name)  # type: ignore[arg-type]

        return orderset

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_enum_type(cls.__enum_type__())

    def __getitem__(cls, models: type[type[TModel]] | tuple[type[TModel], ...]) -> type[OrderSet[*TModels]]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'OrderSet'!
        OrderSetMeta.__models__ = models if isinstance(models, tuple) else (models,)
        return cls  # type: ignore[return-value]

    def __call__(cls, ref: T) -> T:
        """
        Allow adding this OrderSet to a QueryType using a decorator syntax

        >>> class TaskOrderSet(OrderSet[Task]): ...
        >>>
        >>> @TaskOrderSet
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

    def __build__(cls, order_data: list[str], info: GQLInfo) -> OrderResults:
        """
        Build a list of 'OrderBy' expressions from the given order input data.

        :param order_data: The input order data.
        :param info: The GraphQL resolve info for the request.
        """
        order_by: list[OrderBy] = []
        aliases: dict[str, DjangoExpression] = {}
        order_count: int = 0

        for enum_value in order_data:
            if enum_value.endswith("_desc"):
                order_name = enum_value.removesuffix("_desc")
                descending = True
            elif enum_value.endswith("_asc"):
                order_name = enum_value.removesuffix("_asc")
                descending = False
            else:  # pragma: no cover
                raise GraphQLInvalidOrderDataError(orderset=cls, enum_value=enum_value)

            order = cls.__order_map__[order_name]
            if order.aliases_func is not None:
                aliases |= order.aliases_func(order, info, descending=descending)

            expression = order.get_expression(descending=descending)
            order_by.append(expression)
            order_count += 1

        return OrderResults(order_by=order_by, aliases=aliases, order_count=order_count)

    def __enum_type__(cls) -> GraphQLEnumType:
        """Create the enum type to use for the `QueryType` this `OrderSet` is for."""
        return get_or_create_graphql_enum(
            name=cls.__schema_name__,
            values=cls.__enum_values__(),
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )

    def __enum_values__(cls) -> dict[str, GraphQLEnumValue | str]:
        """
        Get all the enum values for this `OrderSet`.
        The values are the names of all the `Order` instances defined on this `OrderSet`,
        in both ascending and descending directions.
        """
        enum_values: dict[str, GraphQLEnumValue | str] = {}

        for ordering in cls.__order_map__.values():
            for descending in (False, True):
                name = ordering.schema_name + ("Desc" if descending else "Asc")
                enum_value = ordering.as_graphql_enum_value()
                enum_value.value += "_desc" if descending else "_asc"
                enum_values[name] = enum_value

        return enum_values

    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        """
        Determine if the given orderset is visible in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.
        """
        return True

    def __add_directive__(cls, directive: Directive, /) -> Self:
        """Add a directive to this orderset."""
        check_directives([directive], location=DirectiveLocation.ENUM)
        cls.__directives__.append(directive)
        return cls

    def __add_to_query_type__(cls, query_type: type[QueryType]) -> None:
        models = cls.__models__
        if len(models) != 1:
            raise QueryTypeRequiresSingleModelError(kind="OrderSet")

        if models[0] is not query_type.__model__:
            raise MismatchingModelError(
                name=cls.__name__,
                given_model=models[0],
                target=query_type.__name__,
                expected_model=query_type.__model__,
            )

        query_type.__orderset__ = cls  # type: ignore[assignment]

    def __add_to_union_type__(cls, union_type: type[UnionType]) -> None:
        models = cls.__models__
        if len(models) == 1:
            raise UnionTypeRequiresMultipleModelsError(kind="OrderSet")

        on_union_type = set(union_type.__query_types_by_model__)
        on_orderset = set(models)

        if on_union_type != on_orderset:
            raise UnionTypeModelsDifferentError(kind="OrderSet")

        union_type.__orderset__ = cls  # type: ignore[assignment]


class OrderSet(Generic[*TModels], metaclass=OrderSetMeta):
    """
    A class for adding ordering for a `QueryType`.

    Must set the Django Model this `OrderSet` is for using the generic type argument.
    Model must match the Model of the `QueryType` this `OrderSet` will be added to.

    The following parameters can be passed in the class definition:

    `auto: bool = <AUTOGENERATION setting>`
        Whether to add `Order` attributes for all Model fields automatically.

    `exclude: list[str] = []`
        Model fields to exclude from automatically added `Order` attributes.

    `schema_name: str = <class name>`
        Override the name for the `GraphQLEnum` for this `OrderSet` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `GraphQLEnum`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `GraphQLEnum`.

    >>> class TaskOrderSet(OrderSet[Task]): ...
    >>> class TaskQueryType(QueryType[Task], orderset=TaskOrderSet): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `Order` names.

    # Set in metaclass
    __models__: ClassVar[tuple[type[Model], ...]]
    __order_map__: ClassVar[dict[str, Order]]
    __schema_name__: ClassVar[str]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]


class Order:
    """
    A class for defining a possible ordering for a QueryType.
    Represents a value in the GraphQL `EnumType` for the `OrderSet` this is added to.

    >>> class TaskOrderSet(OrderSet[Task]):
    ...     name = Order()
    """

    def __init__(self, ref: Any = None, **kwargs: Unpack[OrderParams]) -> None:
        """
        Create a new `Order`.

        :param ref: the expression to order by. Must be convertable by the `convert_to_order_ref` function.
                    If not provided, use the name of the attribute this is assigned to in the `OrderSet` class.
        :param null_placement: Where should null values be placed? By default, use database default.
        :param description: Description of the `Order`.
        :param deprecation_reason: If this `Order` is deprecated, describes the reason for deprecation.
        :param field_name: Name of the field in the Django model. If not provided, use the name of the attribute.
        :param schema_name: Actual name of the `Order` in the GraphQL schema. Can be used to alias the `Order`
                            for the schema, or when the desired name is a Python keyword (e.g. `if` or `from`).
        :param directives: GraphQL directives for the `Order`.
        :param extensions: GraphQL extensions for the `Order`.
        """
        self.ref: Any = ref

        self.nulls_first: bool | None = True if kwargs.get("null_placement") == "first" else None
        self.nulls_last: bool | None = True if kwargs.get("null_placement") == "last" else None
        self.description: str | None = kwargs.get("description", Undefined)  # type: ignore[assignment]
        self.deprecation_reason: str | None = kwargs.get("deprecation_reason")
        self.field_name: str = kwargs.get("field_name", Undefined)  # type: ignore[assignment]
        self.schema_name: str = kwargs.get("schema_name", Undefined)  # type: ignore[assignment]
        self.directives: list[Directive] = kwargs.get("directives", [])
        self.extensions: dict[str, Any] = kwargs.get("extensions", {})

        check_directives(self.directives, location=DirectiveLocation.ENUM_VALUE)
        self.extensions[undine_settings.ORDER_EXTENSIONS_KEY] = self

        self.aliases_func: OrderAliasesFunc | None = None
        self.visible_func: VisibilityFunc | None = None

    def __connect__(self, orderset: type[OrderSet], name: str) -> None:
        """Connect this `Order` to the given `OrderSet` using the given name."""
        self.orderset = orderset
        self.name = name
        self.field_name = self.field_name or name
        self.schema_name = self.schema_name or to_schema_name(name)

        if isinstance(self.ref, str):
            self.field_name = self.ref

        self.ref = convert_to_order_ref(self.ref, caller=self)

        if self.description is Undefined:
            self.description = self.orderset.__attribute_docstrings__.get(name)
            if self.description is None:
                self.description = convert_to_description(self.ref)

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref!r})>"

    def __str__(self) -> str:
        value = self.as_graphql_enum_value()
        return undine_settings.SDL_PRINTER.print_enum_value(self.schema_name, value, indent=False)

    def get_expression(self, *, descending: bool) -> OrderBy:
        return OrderBy(
            expression=self.ref,
            nulls_first=self.nulls_first,
            nulls_last=self.nulls_last,
            descending=descending,
        )

    def as_graphql_enum_value(self) -> GraphQLEnumValue:
        return GraphQLEnumValue(
            value=self.name,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )

    def aliases(self, func: OrderAliasesFunc | None = None, /) -> OrderAliasesFunc:
        """
        Decorate a function to add additional queryset aliases required by this Order.

        >>> class TaskOrderSet(OrderSet[Task]):
        ...     name = Order()
        ...
        ...     @name.aliases
        ...     def name_aliases(self: Order, info: GQLInfo, *, value: str) -> dict[str, DjangoExpression]:
        ...         return {"foo": Value("bar")}
        """
        if func is None:  # Allow `@<order_name>.aliases()`
            return self.aliases  # type: ignore[return-value]
        self.aliases_func = get_wrapped_func(func)
        return func

    def visible(self, func: VisibilityFunc | None = None, /) -> VisibilityFunc:
        """
        Decorate a function to change the Order's visibility in the schema.
        Experimental, requires `EXPERIMENTAL_VISIBILITY_CHECKS` to be enabled.

        >>> class TaskOrderSet(OrderSet[Task]):
        ...     name = Order()
        ...
        ...     @name.visible
        ...     def name_visible(self: Order, request: DjangoRequestProtocol) -> bool:
        ...         return False
        """
        if func is None:  # Allow `@<order_name>.visible()`
            return self.visible  # type: ignore[return-value]
        self.visible_func = get_wrapped_func(func)
        return func

    def add_directive(self, directive: Directive, /) -> Self:
        """Add a directive to this order."""
        check_directives([directive], location=DirectiveLocation.ENUM_VALUE)
        self.directives.append(directive)
        return self


def get_orders_for_model(model: type[Model], *, exclude: Iterable[str] = ()) -> dict[str, Order]:
    """Creates `Orders` for all the given model's fields, except those in the 'exclude' list."""
    result: dict[str, Order] = {}

    for model_field in get_model_fields_for_graphql(model):
        field_name = model_field.name

        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        result[field_name] = Order(field_name)

    return result


def get_orders_for_models(models: tuple[type[Model], ...], exclude: Iterable[str] = ()) -> dict[str, Order]:
    result: dict[str, Order] = {}

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

        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if is_primary_key:
            field_name = "pk"  # noqa: PLW2901

        if field_name in exclude:
            continue

        result[field_name] = Order(field_name)

    return result
