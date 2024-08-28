from __future__ import annotations

import contextlib
from contextlib import suppress
from typing import TYPE_CHECKING, TypeGuard

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, ForeignKey, Model
from graphql import (
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    GraphQLOutputType,
    GraphQLResolveInfo,
    GraphQLUnionType,
    InlineFragmentNode,
)
from graphql.execution.execute import get_field_def

from undine.errors import OptimizerError
from undine.settings import undine_settings
from undine.utils.text import to_snake_case

if TYPE_CHECKING:
    from undine import ModelGQLType
    from undine.typing import ModelField, Selections, ToManyField, ToOneField

__all__ = [
    "GraphQLASTWalker",
]


class GraphQLASTWalker:
    """Class for walking the GraphQL AST and handling the different nodes."""

    def __init__(self, info: GraphQLResolveInfo, model: type[Model] | None = None) -> None:
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
        if field_model is None:
            return self.handle_plain_object_type(field_type, field_node)
        return self.handle_model_field(field_type, field_node, field_name, field_model)

    def handle_graphql_builtin(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None: ...

    def handle_plain_object_type(self, field_type: GraphQLOutputType, field_node: FieldNode) -> None: ...

    def handle_model_field(
        self,
        field_type: GraphQLOutputType,
        field_node: FieldNode,
        field_name: str,
        model: type[Model],
    ) -> None:
        field = get_model_field(model, field_name)

        if field is None:
            with self.use_model(model):
                return self.handle_custom_field(field_type, field_node)

        if not field.is_relation or is_foreign_key_id(field, field_node):
            with self.use_model(model):
                return self.handle_normal_field(field_type, field_node, field)

        if is_to_one(field):
            related_model = get_related_model(field, model)
            with self.use_model(field.model):
                return self.handle_to_one_field(field_type, field_node, field, related_model)

        if is_to_many(field):
            related_model = get_related_model(field, model)
            with self.use_model(model):
                return self.handle_to_many_field(field_type, field_node, field, related_model)

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
        fragment_model: type[Model] = self.get_model(fragment_type)
        if fragment_model != self.model:
            return None

        selections = get_selections(inline_fragment)
        return self.handle_selections(fragment_type, selections)

    def get_model_type(self, field_type: GraphQLOutputType) -> type[ModelGQLType] | None:
        return field_type.extensions.get(undine_settings.MODEL_TYPE_EXTENSIONS_KEY)

    def get_model(self, field_type: GraphQLOutputType) -> type[Model] | None:
        return getattr(self.get_model_type(field_type), "__model__", None)

    def get_field_type(self, parent_type: GraphQLOutputType, field_node: FieldNode) -> GraphQLOutputType:
        graphql_field = get_field_def(self.info.schema, parent_type, field_node)
        return get_underlying_type(graphql_field.type)

    def get_field_name(self, field_node: FieldNode) -> str:
        alias = getattr(field_node.alias, "value", None)
        return alias or to_snake_case(field_node.name.value)

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


def is_to_many(field: Field) -> TypeGuard[ToManyField]:
    return bool(field.one_to_many or field.many_to_many)


def is_to_one(field: Field) -> TypeGuard[ToOneField]:
    return bool(field.many_to_one or field.one_to_one)


def get_fragment_type(field_type: GraphQLUnionType, inline_fragment: InlineFragmentNode) -> GraphQLOutputType:
    fragment_type_name = inline_fragment.type_condition.name.value
    gen = (t for t in field_type.types if t.name == fragment_type_name)
    fragment_type: GraphQLOutputType | None = next(gen, None)

    if fragment_type is None:  # pragma: no cover
        msg = f"Fragment type '{fragment_type_name}' not found in union '{field_type}'"
        raise OptimizerError(msg)

    return fragment_type


def get_related_model(related_field: ToOneField | ToManyField, model: type[Model]) -> type[Model] | None:
    """
    Get the related model for a field.
    Note: For generic foreign keys, the related model is unknown (=None).
    """
    related_model = related_field.related_model
    if related_model == "self":  # pragma: no cover
        return model
    return related_model  # type: ignore[return-value]


def get_model_field(model: type[Model], field_name: str) -> ModelField | None:
    if field_name == "pk":
        return model._meta.pk

    with suppress(FieldDoesNotExist):
        return model._meta.get_field(field_name)

    # Field might be a reverse many-related field without `related_name`, in which case
    # the `model._meta.fields_map` will store the relation without the "_set" suffix.
    if field_name.endswith("_set"):
        with suppress(FieldDoesNotExist):
            model_field: ModelField = model._meta.get_field(field_name.removesuffix("_set"))
            if is_to_many(model_field):
                return model_field

    return None
