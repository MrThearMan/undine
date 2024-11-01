from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from django.db.models import Field, ForeignKey, Model
from graphql import (
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    GraphQLOutputType,
    GraphQLUnionType,
    InlineFragmentNode,
)
from graphql.execution.execute import get_field_def

from undine.errors.exceptions import ModelFieldDoesNotExistError, OptimizerError
from undine.settings import undine_settings
from undine.utils.model_utils import get_model_field, is_to_many, is_to_one
from undine.utils.text import to_snake_case

if TYPE_CHECKING:
    from undine.query import QueryType
    from undine.typing import GQLInfo, ModelField, Selections, ToManyField, ToOneField

__all__ = [
    "GraphQLASTWalker",
]


class GraphQLASTWalker:  # noqa: PLR0904
    """Class for walking the GraphQL AST and handling the different nodes."""

    def __init__(self, info: GQLInfo, model: type[Model] | None = None) -> None:
        self.info = info
        self.complexity: int = 0
        self.model: type[Model] = model

    def increase_complexity(self) -> None:
        self.complexity += 1

    def run(self) -> None:
        return self.handle_selections(self.info.parent_type, self.info.field_nodes)

    def handle_selections(self, field_type: GraphQLOutputType, selections: Selections) -> None:
        for selection in selections:
            if isinstance(selection, FieldNode):
                self.handle_field_node(field_type, selection)

            elif isinstance(selection, FragmentSpreadNode):
                self.handle_fragment_spread(field_type, selection)

            elif isinstance(selection, InlineFragmentNode):
                self.handle_inline_fragment(field_type, selection)

            else:  # pragma: no cover
                msg = f"Unhandled selection node: '{selection}'"
                raise OptimizerError(msg)

    def handle_field_node(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        if self.info.parent_type == field_type:
            return self.handle_query_class(field_type, field_node)
        return self.handle_object_type(field_type, field_node)

    def handle_query_class(self, parent_type: GraphQLOutputType, field_node: FieldNode) -> None:
        field_type = self.get_field_type(parent_type, field_node)
        selections = get_selections(field_node)
        return self.handle_selections(field_type, selections)

    def handle_object_type(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None:
        field_name = to_snake_case(field_node.name.value)
        if is_graphql_builtin(field_name):
            return self.handle_graphql_builtin(field_type, field_node)

        field_model = self.get_model(field_type)
        if field_model is None:  # pragma: no cover
            return None
        return self.handle_model_field(field_type, field_node, field_name, field_model)

    def handle_graphql_builtin(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None: ...

    def handle_model_field(
        self,
        field_type: GraphQLOutputType,
        field_node: FieldNode,
        field_name: str,
        model: type[Model],
    ) -> None:
        try:
            field: ModelField | None = get_model_field(model=model, lookup=field_name)
        except ModelFieldDoesNotExistError:
            field: ModelField | None = None

        if field is None:
            with self.use_model(model):
                return self.handle_custom_field(field_type, field_node)

        if not field.is_relation or is_foreign_key_id(field, field_node):
            with self.use_model(model):
                return self.handle_normal_field(field_type, field_node, field)

        if is_to_one(field):
            with self.use_model(field.model):
                return self.handle_to_one_field(field_type, field_node, field, field.related_model)

        if is_to_many(field):
            with self.use_model(model):
                return self.handle_to_many_field(field_type, field_node, field, field.related_model)

        msg = f"Unhandled field: '{field.name}'"  # pragma: no cover
        raise OptimizerError(msg)  # pragma: no cover

    def handle_custom_field(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None: ...

    def handle_normal_field(self, field_type: GraphQLOutputType, field_node: FieldNode, field: Field) -> None: ...

    def handle_to_one_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[Model] | None,
    ) -> None:
        field_type = self.get_field_type(parent_type, field_node)
        selections = get_selections(field_node)
        self.increase_complexity()
        return self.handle_selections(field_type, selections)

    def handle_to_many_field(
        self,
        parent_type: GraphQLOutputType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[Model] | None,
    ) -> None:
        field_type = self.get_field_type(parent_type, field_node)
        selections = get_selections(field_node)
        self.increase_complexity()
        return self.handle_selections(field_type, selections)

    def handle_fragment_spread(self, field_type: GraphQLOutputType, fragment_spread: FragmentSpreadNode) -> None:
        fragment_definition = self.info.fragments[fragment_spread.name.value]
        selections = get_selections(fragment_definition)
        return self.handle_selections(field_type, selections)

    def handle_inline_fragment(self, field_type: GraphQLUnionType, inline_fragment: InlineFragmentNode) -> None:
        fragment_type = get_fragment_type(field_type, inline_fragment)
        fragment_model = self.get_model(fragment_type)
        if fragment_model is None:  # pragma: no cover
            return None
        if fragment_model != self.model:
            return None

        # TODO: Test when unions are supported.
        selections = get_selections(inline_fragment)  # pragma: no cover
        return self.handle_selections(fragment_type, selections)  # pragma: no cover

    def get_model_type(self, field_type: GraphQLOutputType) -> type[QueryType] | None:
        return field_type.extensions.get(undine_settings.QUERY_TYPE_EXTENSIONS_KEY)

    def get_model(self, field_type: GraphQLOutputType) -> type[Model] | None:
        return getattr(self.get_model_type(field_type), "__model__", None)

    def get_field_type(self, parent_type: GraphQLOutputType, field_node: FieldNode) -> GraphQLOutputType:
        graphql_field = get_field_def(self.info.schema, parent_type, field_node)
        return get_underlying_type(graphql_field.type)

    def get_field_name(self, field_node: FieldNode) -> str:
        alias = getattr(field_node.alias, "value", None)
        return alias or to_snake_case(field_node.name.value)

    def get_related_field_name(self, related_field: ToManyField | ToOneField) -> str:
        if hasattr(related_field, "cache_name"):  # Django 5.1+
            return related_field.cache_name or related_field.name  # pragma: no cover
        return related_field.get_cache_name() or related_field.name  # pragma: no cover

    @contextlib.contextmanager
    def use_model(self, model: type[Model]) -> GraphQLASTWalker:
        orig_model = self.model
        try:
            self.model = model
            yield
        finally:
            self.model = orig_model


GRAPHQL_BUILTIN = (
    "__typename",
    "__schema",
    "__type",
    "__typekind",
    "__field",
    "__inputvalue",
    "__enumvalue",
    "__directive",
)


def get_underlying_type(field_type: GraphQLOutputType) -> GraphQLOutputType:
    while hasattr(field_type, "of_type"):
        field_type = field_type.of_type
    return field_type


def get_selections(field_node: FieldNode | FragmentDefinitionNode | InlineFragmentNode) -> Selections:
    return getattr(field_node.selection_set, "selections", ())


def is_graphql_builtin(field_name: str) -> bool:
    return field_name.lower() in GRAPHQL_BUILTIN


def is_foreign_key_id(field: Field, field_node: FieldNode) -> bool:
    return isinstance(field, ForeignKey) and field.get_attname() == to_snake_case(field_node.name.value)


def get_fragment_type(field_type: GraphQLUnionType, inline_fragment: InlineFragmentNode) -> GraphQLOutputType:
    fragment_type_name = inline_fragment.type_condition.name.value
    gen = (t for t in field_type.types if t.name == fragment_type_name)
    fragment_type: GraphQLOutputType | None = next(gen, None)

    if fragment_type is None:  # pragma: no cover
        msg = f"Fragment type '{fragment_type_name}' not found in union '{field_type}'"
        raise OptimizerError(msg)

    return fragment_type
