from __future__ import annotations

from functools import cache
from typing import Any

from django.db import models
from graphql import GraphQLInputField, GraphQLInputObjectType, Undefined

from undine.typing import CombinableExpression, FilterResults, GQLInfo
from undine.utils.text import get_docstring

from .metaclasses.model_filter_meta import ModelGQLFilterMeta


class ModelGQLFilter(metaclass=ModelGQLFilterMeta, model=Undefined):
    """
    Base class for creating filters for a `ModelGQLType`.
    Creates a single GraphQL InputObjectType from filters defined in the class,
    which can then be combined using logical operators.

    The following parameters can be passed in the class definition:

    - `model`: Set the Django model this `ModelGQLFilter` is for. This input is required.
               Must match the model of the `ModelGQLType` this `ModelGQLFilter` is for.
    - `auto_filters`: Whether to add filters for all model fields and their lookups automatically. Defaults to `True`.
    - `exclude`: List of model fields to exclude from the automatically added filters. No excludes by default.
    - `name`: Override name for the input object type in the GraphQL schema. Use class name by default.
    - `extensions`: GraphQL extensions for the created `InputObjectType`. Defaults to `None`.

    >>> class MyFilters(ModelGQLFilter, model=...): ...
    """

    # Members should use `__dunder__` names to avoid name collisions with possible filter names.

    @classmethod
    def __build__(cls, filter_data: dict[str, Any], info: GQLInfo, *, op: str = "AND") -> FilterResults:
        """
        Build a Q-object from the given filter data.
        Also indicate whether the filter should be distinct based on the fields in the filter data.

        :param filter_data: A map of filter schema names to input values.
        :param info: The GraphQL resolve info for the request.
        :param op: The logical operator to use for combining multiple filters.
        """
        q: models.Q = models.Q()
        distinct: bool = False
        aliases: dict[str, CombinableExpression] = {}

        for filter_name, filter_value in filter_data.items():
            if filter_name in ("AND", "OR", "XOR", "NOT"):
                results = cls.__build__(filter_value, info, op=filter_name)
                filter_expression = results.q
                distinct = distinct or results.distinct
                aliases |= results.aliases

            else:
                filter_ = cls.__filter_map__[filter_name]
                distinct = distinct or filter_.distinct
                filter_expression = filter_.get_expression(filter_value, info)
                if isinstance(filter_.ref, (models.Expression, models.Subquery)):
                    aliases[filter_.name] = filter_.ref

            if op == "AND":
                q &= filter_expression
            elif op == "OR":
                q |= filter_expression
            elif op == "NOT":
                q = ~filter_expression
            elif op == "XOR":
                q ^= filter_expression

        return FilterResults(q=q, distinct=distinct, aliases=aliases)

    @classmethod
    @cache
    def __input_type__(cls) -> GraphQLInputObjectType:
        """
        Create a `GraphQLInputObjectType` for this class.
        Cache the result since a GraphQL schema cannot contain multiple types with the same name.
        """
        input_object_type = GraphQLInputObjectType(
            name=cls.__typename__,
            description=get_docstring(cls),
            fields={},
            extensions=cls.__extensions__,
        )

        def _get_fields() -> dict[str, GraphQLInputField]:
            fields = {name: filter_.as_input_field() for name, filter_ in cls.__filter_map__.items()}
            fields["AND"] = fields["OR"] = fields["NOT"] = fields["XOR"] = GraphQLInputField(type_=input_object_type)
            return fields

        input_object_type._fields = _get_fields
        return input_object_type
