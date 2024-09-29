from __future__ import annotations

from graphql import GraphQLEnumType, GraphQLEnumValue, Undefined

from undine.typing import GQLInfo, OrderingResults
from undine.utils.decorators import cached_class_method
from undine.utils.text import get_docstring

from .metaclasses.model_ordering_meta import ModelGQLOrderingMeta

__all__ = [
    "ModelGQLOrdering",
]


class ModelGQLOrdering(metaclass=ModelGQLOrderingMeta, model=Undefined):
    """
    Base class for creating options for ordering a `ModelGQLType`.
    Creates a single GraphQL Enum from orderings defined in the class,
    which can then be combined using a list for the desired ordering.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this ModelGQLOrdering is for. This input is required.
               Must match the model of the `ModelGQLType` this `ModelGQLOrdering` is for.
    - `auto_ordering`: Whether to add ordering fields for all given model's fields automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from automatically added ordering fields. No excludes by default.
    - `name`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created GraphQLEnum. Defaults to `None`.

    >>> class MyOrdering(ModelGQLOrdering, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible ordering field names.

    @classmethod
    def __build__(cls, ordering_data: list[str], info: GQLInfo) -> OrderingResults:
        """
        Build a list of ordering expressions from the given ordering data.

        :param ordering_data: A list of ordering schema names.
        :param info: The GraphQL resolve info for the request.
        """
        result = OrderingResults(order_by=[])

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
