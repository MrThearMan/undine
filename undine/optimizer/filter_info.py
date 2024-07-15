from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from graphql import FieldNode, GraphQLOutputType, GraphQLResolveInfo, get_argument_values
from graphql.execution.execute import get_field_def

from undine.settings import undine_settings
from undine.typing import GraphQLFilterInfo, ToManyField, ToOneField
from undine.utils.reflection import swappable_by_subclassing
from undine.utils.text import to_snake_case

from .ast import GraphQLASTWalker, get_underlying_type

if TYPE_CHECKING:
    from django.db import models


__all__ = [
    "get_filter_info",
]


def get_filter_info(info: GraphQLResolveInfo, model: type[models.Model]) -> GraphQLFilterInfo:
    """Compile filter information included in the GraphQL query."""
    compiler = FilterInfoCompiler(info, model)
    compiler.run()
    # Return the compiled filter info, or an empty dict if there is no filter info.
    name = getattr(info.field_nodes[0].alias, "value", None) or to_snake_case(info.field_name)
    return compiler.filter_info.get(name, {})


@swappable_by_subclassing
class FilterInfoCompiler(GraphQLASTWalker):
    """Class for compiling filtering information from a GraphQL query."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.filter_info: dict[str, GraphQLFilterInfo] = {}
        super().__init__(*args, **kwargs)

    def add_filter_info(self, parent_type: GraphQLOutputType, field_node: FieldNode) -> None:
        graphql_field = get_field_def(self.info.schema, parent_type, field_node)
        object_type = get_underlying_type(graphql_field.type)
        field_name = self.get_field_name(field_node)

        filters: models.Q | None = None
        distinct: bool = False
        aliases: dict[str, models.Expression | models.Subquery] = {}
        order_by: list[models.OrderBy] = []

        arg_values = get_argument_values(graphql_field, field_node, self.info.variable_values)
        model_type = self.get_model_type(object_type)
        if model_type is not None:
            if model_type.__filters__:
                filter_data = arg_values.get(undine_settings.FILTER_INPUT_TYPE_KEY, {})
                filter_results = model_type.__filters__.__build__(filter_data, self.info)
                filters = filter_results.q
                distinct = filter_results.distinct
                aliases = filter_results.aliases
            if model_type.__ordering__:
                ordering_data = arg_values.get(undine_settings.ORDERING_INPUT_TYPE_KEY, [])
                ordering_results = model_type.__ordering__.__build__(ordering_data, self.info)
                order_by = ordering_results.order_by

        self.filter_info[field_name] = GraphQLFilterInfo(
            model_type=model_type,
            filters=filters,
            distinct=distinct,
            aliases=aliases,
            order_by=order_by,
        )

    def handle_query_class(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        self.add_filter_info(field_type, field_node)
        with self.child_filter_info(field_node):
            return super().handle_query_class(field_type, field_node)

    def handle_custom_field(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        return self.add_filter_info(field_type, field_node)

    def handle_to_one_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[models.Model] | None,
    ) -> None:
        self.add_filter_info(parent_type, field_node)
        with self.child_filter_info(field_node):
            return super().handle_to_one_field(parent_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[models.Model] | None,
    ) -> None:
        self.add_filter_info(parent_type, field_node)
        with self.child_filter_info(field_node):
            return super().handle_to_many_field(parent_type, field_node, related_field, related_model)

    @contextlib.contextmanager
    def child_filter_info(self, field_node: FieldNode) -> None:
        field_name = self.get_field_name(field_node)
        arguments: dict[str, GraphQLFilterInfo] = {}
        orig_arguments = self.filter_info
        try:
            self.filter_info = arguments
            yield
        finally:
            self.filter_info = orig_arguments
            if arguments:
                self.filter_info[field_name].children = arguments
