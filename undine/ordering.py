from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, Unpack

from django.db.models import OrderBy
from graphql import DirectiveLocation, GraphQLEnumValue, Undefined

from undine.converters import convert_to_description, convert_to_order_ref
from undine.dataclasses import OrderResults
from undine.exceptions import GraphQLInvalidOrderDataError, MissingModelGenericError
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.graphql.type_registry import get_or_create_graphql_enum
from undine.utils.graphql.utils import check_directives
from undine.utils.model_utils import get_model_fields_for_graphql
from undine.utils.reflection import get_members
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from collections.abc import Container

    from django.db.models import Model
    from graphql import GraphQLEnumType

    from undine.directives import Directive
    from undine.typing import GQLInfo, OrderParams, OrderSetParams

__all__ = [
    "Order",
    "OrderSet",
]


class OrderSetMeta(type):
    """A metaclass that modifies how an `OrderSet` is created."""

    # Set in '__new__'
    __model__: type[Model]
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
            model = OrderSetMeta.__model__
            del OrderSetMeta.__model__
        except AttributeError as error:
            raise MissingModelGenericError(name=_name, cls="OrderSet") from error

        auto = kwargs.get("auto", True)
        exclude = set(kwargs.get("exclude", []))
        if auto:
            exclude |= set(_attrs)
            _attrs |= get_orders_for_model(model, exclude=exclude)

        orderset = super().__new__(cls, _name, _bases, _attrs)

        # Members should use `__dunder__` names to avoid name collisions with possible `Order` names.
        orderset.__model__ = model
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

    def __getitem__(cls, model: type[TModel]) -> type[OrderSet[TModel]]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'OrderSet'!
        OrderSetMeta.__model__ = model
        return cls  # type: ignore[return-value]

    def __build__(cls, order_data: list[str], info: GQLInfo) -> OrderResults:
        """
        Build a list of 'OrderBy' expressions from the given order input data.

        :param order_data: The input order data.
        :param info: The GraphQL resolve info for the request.
        """
        order_by: list[OrderBy] = []
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
            expression = order.get_expression(descending=descending)
            order_by.append(expression)
            order_count += 1

        return OrderResults(order_by=order_by, order_count=order_count)

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


class OrderSet(Generic[TModel], metaclass=OrderSetMeta):
    """
    A class for adding ordering for a `QueryType`.

    Must set the Django Model this `OrderSet` is for using the generic type argument.
    Model must match the Model of the `QueryType` this `OrderSet` will be added to.

    The following parameters can be passed in the class definition:

    `auto: bool = True`
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
    __model__: ClassVar[type[Model]]
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


def get_orders_for_model(model: type[Model], *, exclude: Container[str] = ()) -> dict[str, Order]:
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
