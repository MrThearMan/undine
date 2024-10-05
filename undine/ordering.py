"""Contains code for creating ordering options for a `QueryType`."""

from __future__ import annotations

from typing import Any, Container, Iterable, Literal

from django.db import models
from graphql import GraphQLEnumType, GraphQLEnumValue, Undefined

from undine.converters import convert_to_description, convert_to_order_ref
from undine.errors.exceptions import MissingModelError
from undine.settings import undine_settings
from undine.typing import GQLInfo, OrderResults
from undine.utils.decorators import cached_class_method
from undine.utils.reflection import get_members
from undine.utils.text import dotpath, get_docstring, get_schema_name

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
        model: type[models.Model] | None = None,
        auto: bool = True,
        exclude: Iterable[str] = (),
        typename: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> OrderSetMeta:
        """See `OrderSet` for documentation of arguments."""
        if model is Undefined:  # Early return for the `OrderSet` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if model is None:
            raise MissingModelError(name=_name, cls="OrderSet")

        if auto:
            _attrs |= get_orders_for_model(model, exclude=set(exclude) | set(_attrs))

        # Add model to attrs before class creation so that it's available during `Order.__set_name__`.
        _attrs["__model__"] = model
        instance: type[OrderSet] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible ordering names.
        instance.__model__ = model
        instance.__order_map__ = {get_schema_name(n): o for n, o in get_members(instance, Order)}
        instance.__typename__ = typename or _name
        instance.__extensions__ = (extensions or {}) | {undine_settings.ORDER_BY_EXTENSIONS_KEY: instance}
        return instance


class OrderSet(metaclass=OrderSetMeta, model=Undefined):
    """
    A class representing a `GraphQLEnumType` used for ordering a `QueryType`.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this OrderSet is for. This input is required.
               Must match the model of the `QueryType` this `OrderSet` is for.
    - `auto`: Whether to add undine.Order fields for all model fields (in both ascending and descending directions)
              automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from automatically added ordering fields. No excludes by default.
    - `typename`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created GraphQLEnum. Defaults to `None`.

    >>> class MyOrder(OrderSet, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible `undine.Order` names.

    @classmethod
    def __build__(cls, order_data: list[str], info: GQLInfo) -> OrderResults:
        """
        Build a list of 'models.OrderBy' expressions from the given Order names.

        :param order_data: The data to build 'order_by' expressions from.
        :param info: The GraphQL resolve info for the request.
        """
        result = OrderResults(order_by=[])

        for name in order_data:
            if name.endswith("Desc"):
                order_name = name.removesuffix("Desc")
                descending = True
            elif name.endswith("Asc"):
                order_name = name.removesuffix("Asc")
                descending = False
            else:  # Single direction ordering.
                order_name = name
                descending = False

            order = cls.__order_map__[order_name]
            expression = order.get_expression(descending=descending)
            result.order_by.append(expression)

        return result

    @cached_class_method
    def __enum_type__(cls) -> GraphQLEnumType:
        """
        Create a `GraphQLEnumType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """
        enum_values: dict[str, GraphQLEnumValue] = {}
        for name, ordering in cls.__order_map__.items():
            if ordering.single_direction:
                enum_values[name] = ordering.get_graphql_enum_value()
                continue

            for direction in ("Asc", "Desc"):
                enum_values[f"{name}{direction}"] = ordering.get_graphql_enum_value()

        return GraphQLEnumType(
            name=cls.__typename__,
            values=enum_values,
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )


class Order:
    def __init__(
        self,
        ref: Any = None,
        *,
        null_placement: Literal["first", "last"] | None = None,
        single_direction: bool = False,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a `GraphQLEnumValue` used for ordering a `QueryType`.

        :param ref: Expression to order by. Can be anything that `convert_to_order_ref` can convert,
                    e.g., a string referencing a model field name, an `F` expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `OrderSet` class.
        :param null_placement: Where should null values be placed? By default, use database default.
        :param single_direction: Set to `True` if the Order supports only a single direction.
        :param description: Description of the Order. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If this Order is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the Order.
        """
        self.ref = ref
        self.description = description
        self.nulls_first = True if null_placement == "first" else None
        self.nulls_last = True if null_placement == "last" else None
        self.single_direction = single_direction
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.ORDER_BY_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[OrderSet], name: str) -> None:
        self.owner = owner
        self.name = name
        self.ref = convert_to_order_ref(self.ref, caller=self)

        if self.description is Undefined:
            self.description = convert_to_description(self.ref)

    def __repr__(self) -> str:
        return f"<{dotpath(self.__class__)}(ref={self.ref})>"

    def get_expression(self, *, descending: bool = False) -> models.OrderBy:
        return models.OrderBy(self.ref, nulls_first=self.nulls_first, nulls_last=self.nulls_last, descending=descending)

    def get_graphql_enum_value(self) -> GraphQLEnumValue:
        return GraphQLEnumValue(
            value=self.name,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )


def get_orders_for_model(model: type[models.Model], *, exclude: Container[str]) -> dict[str, Order]:
    """Creates undine.Order for all of the given model's non-related fields, except those in the 'exclude' list."""
    result: dict[str, Order] = {}
    for model_field in model._meta._get_fields(reverse=False):
        if model_field.is_relation:
            continue

        field_name = model_field.name
        is_primary_key = bool(getattr(model_field, "primary_key", False))
        if undine_settings.USE_PK_FIELD_NAME and is_primary_key:
            field_name = "pk"

        if field_name in exclude:
            continue

        result[field_name] = Order(field_name)

    return result
