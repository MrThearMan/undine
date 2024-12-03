from __future__ import annotations

from typing import TYPE_CHECKING, Any, Container, Iterable, Literal

from django.db import models
from graphql import GraphQLEnumValue, GraphQLList, GraphQLNonNull, Undefined

from undine.converters import convert_to_order_ref
from undine.dataclasses import OrderResults
from undine.errors.exceptions import GraphQLBadOrderDataError, MissingModelError
from undine.parsers import parse_description
from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_graphql_enum
from undine.utils.model_utils import get_lookup_field_name, get_model_fields_for_graphql
from undine.utils.reflection import get_members
from undine.utils.text import dotpath, get_docstring, to_schema_name

if TYPE_CHECKING:
    from undine.typing import GQLInfo

__all__ = [
    "Order",
    "OrderSet",
]


class OrderSetMeta(type):
    """A metaclass that modifies how a `OrderSet` is created."""

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        *,
        # See `OrderSet` for documentation of arguments.
        model: type[models.Model] | None = None,
        auto: bool = True,
        exclude: Iterable[str] = (),
        typename: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> OrderSetMeta:
        if model is Undefined:  # Early return for the `OrderSet` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="OrderSet")

        if auto:
            _attrs |= get_orders_for_model(model, exclude=set(exclude) | set(_attrs))

        # Add to attrs things that need to be available during `Order.__set_name__`.
        _attrs["__model__"] = model
        instance: type[OrderSet] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use `__dunder__` names to avoid name collisions with possible `undine.Order` names.
        instance.__model__ = model
        instance.__order_map__ = dict(get_members(instance, Order))
        instance.__typename__ = typename or _name
        instance.__extensions__ = (extensions or {}) | {undine_settings.ORDERSET_EXTENSIONS_KEY: instance}
        return instance


class OrderSet(metaclass=OrderSetMeta, model=Undefined):
    """
    A class representing a GraphQL Input Object Type for ordering the results of a query base on a QueryType.
    Can be added to a QueryType in the QueryType's class definition.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this OrderSet is for. This input is required.
               Must match the model of the `QueryType` this `OrderSet` is for.
    - `auto`: Whether to add undine.Order fields for all model fields (in both ascending and descending directions)
              automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from automatically added ordering fields. No excludes by default.
    - `typename`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created GraphQLEnum. Defaults to `None`.

    >>> class MyOrderSet(OrderSet, model=...): ...
    >>> class MyQueryType(QueryType, model=..., orderset=MyOrderSet): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `undine.Order` names.

    @classmethod
    def __build__(cls, order_data: list[str], info: GQLInfo) -> OrderResults:
        """
        Build a list of 'models.OrderBy' expressions from the given order input data.

        :param order_data: The input order data.
        :param info: The GraphQL resolve info for the request.
        """
        result = OrderResults(order_by=[])

        for enum_value in order_data:
            if enum_value.endswith("_desc"):
                order_name = enum_value.removesuffix("_desc")
                descending = True
            elif enum_value.endswith("_asc"):
                order_name = enum_value.removesuffix("_asc")
                descending = False
            else:  # pragma: no cover
                raise GraphQLBadOrderDataError(orderset=cls, enum_value=enum_value)

            order = cls.__order_map__[order_name]
            expression = order.get_expression(descending=descending)
            result.order_by.append(expression)

        return result

    @classmethod
    def __input_type__(cls) -> GraphQLList:
        """
        Create the input type for this OrderSet.
        The input is a non-null list of a GraphQL Enum
        consisting of all the `undine.Order` names defined on this OrderSet,
        in both ascending and descending directions.
        """
        enum_values: dict[str, GraphQLEnumValue] = {}
        for ordering in cls.__order_map__.values():
            for descending in (False, True):
                enum_value = ordering.get_graphql_enum_value(descending=descending)
                enum_values[to_schema_name(enum_value.value)] = enum_value

        enum_type = get_or_create_graphql_enum(
            name=cls.__typename__,
            values=enum_values,
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )
        return GraphQLList(GraphQLNonNull(enum_type))


class Order:
    def __init__(
        self,
        ref: Any = None,
        *,
        null_placement: Literal["first", "last"] | None = None,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a possible ordering for a QueryType.
        Can be added to the class body of a `OrderSet` class.

        :param ref: Expression to order by. Can be anything that `convert_to_order_ref` can convert,
                    e.g., a string referencing a model field name, an `F` expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `OrderSet` class.
        :param null_placement: Where should null values be placed? By default, use database default.
        :param description: Description of the Order. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If this Order is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the Order.
        """
        self.ref = ref
        self.description = description
        self.nulls_first = True if null_placement == "first" else None
        self.nulls_last = True if null_placement == "last" else None
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.ORDER_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[OrderSet], name: str) -> None:
        self.owner = owner
        self.name = name
        self.ref = convert_to_order_ref(self.ref, caller=self)

        if self.description is Undefined:
            self.description = parse_description(self.ref)

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref})>"

    def get_expression(self, *, descending: bool) -> models.OrderBy:
        return models.OrderBy(
            expression=self.ref,
            nulls_first=self.nulls_first,
            nulls_last=self.nulls_last,
            descending=descending,
        )

    def get_graphql_enum_value(self, *, descending: bool) -> GraphQLEnumValue:
        return GraphQLEnumValue(
            value=self.name + ("_desc" if descending else "_asc"),
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )


def get_orders_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Order]:
    """Creates undine.Order for all of the given model's non-related fields, except those in the 'exclude' list."""
    result: dict[str, Order] = {}
    for model_field in get_model_fields_for_graphql(model, include_relations=False):
        field_name = model_field.name

        is_primary_key = bool(getattr(model_field, "primary_key", False))

        if is_primary_key:
            field_name = get_lookup_field_name(model)

        if field_name in exclude:
            continue

        result[field_name] = Order(field_name)

    return result
