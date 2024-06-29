from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.constants import LOOKUP_SEP
from graphql import GraphQLArgument, GraphQLList, GraphQLNonNull, Undefined

from undine.converters import convert_model_field_to_graphql_input_type
from undine.metaclasses import ModelGQLFiltersMeta
from undine.parsers import parse_model_field
from undine.settings import undine_settings

if TYPE_CHECKING:
    from undine import ModelGQLType


__all__ = [
    "Filter",
    "ModelGQLFilters",
]


class ModelGQLFilters(metaclass=ModelGQLFiltersMeta, model=Undefined):
    """Base class for hoding filters used for a ModelGQLType."""

    # Members should use `__dunder__` names to avoid name collisions with possible field names.


class Filter:
    def __init__(  # noqa: PLR0913
        self,
        *,
        field_name: str | None = None,
        lookup_expr: str = "exact",
        default_value: Any = Undefined,
        required: bool = False,
        distinct: bool = False,
        description: str | None = None,
        deprecation_reason: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        """
        A class representing a GraphQL Argument used for filtering a ModelGQLType.

        :param field_name: Name of the field to filter. If not provided, the name of the filter
                           will be the same as the name of the field.
        :param lookup_expr: Lookup expression to use for the filter.
        :param default_value: Default value for the filter if none is provided.
        :param required: Whether the filter should be required.
        :param distinct: Whether the filter required `qs.distinct()` to be used.
        :param description: Description of the filter.
        :param deprecation_reason: If the field is deprecated, describes the reason for deprecation.
        :param extensions: GraphQL extensions for the filter.
        """
        self.field_name: str = field_name
        self.lookup_expr = lookup_expr
        self.default_value = default_value
        self.required = required
        self.many = lookup_expr == "in"  # TODO: Probably other ones too
        self.distinct = distinct
        self.description = description
        self.deprecation_reason = deprecation_reason
        self.extensions = extensions or {}
        self.extensions[undine_settings.FILTER_EXTENSIONS_KEY] = self

    def __set_name__(self, owner: type[ModelGQLType], name: str) -> None:
        self.owner = owner
        self.name = name
        self.field_name = self.field_name or name

    def get_q_expression(self, value: Any) -> models.Q:
        if value is Undefined:
            value = self.default_value
            if value is Undefined:
                return models.Q()

        lookup = f"{self.field_name}{LOOKUP_SEP}{self.lookup_expr}"
        return models.Q(**{lookup: value})

    def as_argument(self) -> GraphQLArgument:
        model_field = parse_model_field(model=self.owner.__model__, lookup=self.field_name)
        graphql_type = convert_model_field_to_graphql_input_type(model_field)

        if self.many:
            if not model_field.null:
                graphql_type = GraphQLNonNull(graphql_type)
            graphql_type = GraphQLList(graphql_type)

        if self.required:
            graphql_type = GraphQLNonNull(graphql_type)

        return GraphQLArgument(
            type_=graphql_type,
            default_value=self.default_value,
            description=self.description,
            deprecation_reason=self.deprecation_reason,
            extensions=self.extensions,
        )
