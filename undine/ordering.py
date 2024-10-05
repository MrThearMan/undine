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
        auto_ordering: bool = True,
        exclude: Iterable[str] = (),
        typename: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> OrderSetMeta:
        """See `OrderSet` for documentation of arguments."""
        if model is Undefined:  # Early return for the `OrderSet` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        if models is None:
            raise MissingModelError(name=_name, cls="OrderSet")

        if auto_ordering:
            _attrs |= get_orders_for_model(model, exclude=set(exclude) | set(_attrs))

        # Add model to attrs before class creation so that it's available during `Order.__set_name__`.
        _attrs["__model__"] = model
        instance: type[OrderSet] = super().__new__(cls, _name, _bases, _attrs)  # type: ignore[assignment]

        # Members should use '__dunder__' names to avoid name collisions with possible ordering names.
        instance.__model__ = model
        instance.__ordering_map__ = {get_schema_name(n): o for n, o in get_members(instance, Order)}
        instance.__typename__ = typename or _name
        instance.__extensions__ = extensions or {} | {undine_settings.ORDER_BY_EXTENSIONS_KEY: instance}
        return instance


class OrderSet(metaclass=OrderSetMeta, model=Undefined):
    """
    Base class for creating options for ordering a `QueryType`.
    Creates a single GraphQL Enum from orderings defined in the class,
    which can then be combined using a list for the desired ordering.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this OrderSet is for. This input is required.
               Must match the model of the `QueryType` this `OrderSet` is for.
    - `auto_ordering`: Whether to add ordering fields for all given model's fields automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from automatically added ordering fields. No excludes by default.
    - `typename`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created GraphQLEnum. Defaults to `None`.

    >>> class MyOrder(OrderSet, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible ordering field names.

    @classmethod
    def __build__(cls, ordering_data: list[str], info: GQLInfo) -> OrderResults:
        """
        Build a list of ordering expressions from the given ordering data.

        :param ordering_data: A list of ordering schema names.
        :param info: The GraphQL resolve info for the request.
        """
        result = OrderResults(order_by=[])

        for ordering_item in ordering_data:
            if ordering_item.endswith("Desc"):
                filter_name = ordering_item[:-4]
                descending = True
            elif ordering_item.endswith("Asc"):
                filter_name = ordering_item[:-3]
                descending = False
            else:  # Does not support reversing order.
                filter_name = ordering_item
                descending = False

            ordering_ = cls.__ordering_map__[filter_name]
            result.order_by.append(ordering_.get_expression(descending=descending))

        return result

    @cached_class_method
    def __enum_type__(cls) -> GraphQLEnumType:
        """
        Create a `GraphQLEnumType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """
        enum_values: dict[str, GraphQLEnumValue] = {}
        for name, ordering in cls.__ordering_map__.items():
            if not ordering.supports_reversing:
                enum_values[name] = GraphQLEnumValue(value=name, description=ordering.description)
                continue

            for direction in ("Asc", "Desc"):
                schema_name = f"{name}{direction}"
                enum_values[schema_name] = GraphQLEnumValue(value=schema_name, description=ordering.description)

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
        null_order: Literal["first", "last"] | None = None,
        supports_reversing: bool = True,
        description: str | None = Undefined,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a GraphQL argument used for ordering a `QueryType`.

        :param ref: Expression to order by. Can be anything that `convert_to_ordering_ref` can convert,
                    e.g., a string referencing a model field name, an `F` expression, a function, etc.
                    If not provided, use the name of the attribute this is assigned to
                    in the `OrderSet` class.
        :param null_order: Where should null values be ordered? By default, use database default.
        :param supports_reversing: Whether the ordering supports both ascending and descending order.
                                   If `True`, this ordering will only add one option for decending order
                                   to the ordering filter instead of ascending and descending variants.
        :param description: Description of the ordering. If not provided, looks at the converted reference,
                            and tries to find the description from it.
        :param deprecation_reason: If this ordering is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the ordering.
        """
        self.ref = ref
        self.description = description
        self.nulls_first = True if null_order == "first" else None
        self.nulls_last = True if null_order == "last" else None
        self.supports_reversing = supports_reversing
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
