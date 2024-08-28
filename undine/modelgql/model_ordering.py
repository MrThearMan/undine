from __future__ import annotations

from graphql import Undefined

from undine.typing import OrderingResults

from .metaclasses.model_ordering_meta import ModelGQLOrderingMeta


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
    def __build__(cls, ordering_data: list[str]) -> OrderingResults:
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
