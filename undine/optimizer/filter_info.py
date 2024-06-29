from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from graphql import FieldNode, GraphQLOutputType, GraphQLResolveInfo, get_argument_values
from graphql.execution.execute import get_field_def

from undine.settings import undine_settings
from undine.typing import GraphQLFilterInfo, ToManyField, ToOneField
from undine.utils import camel_case_to_name
from undine.utils.reflection import swappable_by_subclassing

from .ast import GraphQLASTWalker, get_underlying_type

if TYPE_CHECKING:
    from django.db.models import Model, Q

    from undine import ModelGQLType


__all__ = [
    "get_filter_info",
]


def get_filter_info(info: GraphQLResolveInfo, model: type[Model]) -> GraphQLFilterInfo:
    """Compile filter information included in the GraphQL query."""
    compiler = FilterInfoCompiler(info, model)
    compiler.run()
    # Return the compiled filter info, or an empty dict if there is no filter info.
    alias = getattr(info.field_nodes[0].alias, "value", None)
    return compiler.filter_info.get(camel_case_to_name(alias or info.field_name), {})


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

        filter_values: dict[str, Q] = {}
        distinct: bool = False
        model_type: type[ModelGQLType] | None = object_type.extensions.get(undine_settings.MODEL_TYPE_EXTENSIONS_KEY)
        if model_type is not None and model_type.__filters__:
            arg_values = get_argument_values(graphql_field, field_node, self.info.variable_values)
            for name, value in arg_values.items():
                frt = model_type.__filters__.get(name)
                if frt is not None:
                    filter_values[name] = frt.get_q_expression(value)
                    if frt.distinct:
                        distinct = True

        self.filter_info[field_name] = GraphQLFilterInfo(
            model_type=model_type,
            filters=filter_values,
            distinct=distinct,
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
        related_model: type[Model] | None,
    ) -> None:
        self.add_filter_info(parent_type, field_node)
        with self.child_filter_info(field_node):
            return super().handle_to_one_field(parent_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[Model] | None,
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
