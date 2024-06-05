from __future__ import annotations

import itertools
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from graphql import (
    FieldNode,
    FragmentSpreadNode,
    GraphQLInterfaceType,
    GraphQLResolveInfo,
    GraphQLUnionType,
    InlineFragmentNode,
)
from graphql.execution.collect_fields import get_field_entry_key
from graphql.execution.execute import get_field_def

from undine.dataclasses import AbstractSelections
from undine.exceptions import GraphQLOptimizerError, ModelFieldError
from undine.settings import undine_settings
from undine.utils.graphql.undine_extensions import get_undine_interface_type, get_undine_query_type
from undine.utils.graphql.utils import (
    get_underlying_type,
    is_connection,
    is_edge,
    is_node_interface,
    is_page_info,
    is_relation_id,
    is_typename_metafield,
    should_skip_node,
)
from undine.utils.model_utils import get_model_field, is_generic_foreign_key, is_to_many, is_to_one
from undine.utils.text import to_snake_case

if TYPE_CHECKING:
    from collections.abc import Generator

    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models import Field, Model
    from graphql import (
        FragmentDefinitionNode,
        GraphQLAbstractType,
        GraphQLCompositeType,
        GraphQLNamedOutputType,
        GraphQLObjectType,
        GraphQLScalarType,
    )

    from undine.typing import GQLInfo, ModelField, ObjectSelections, Selections, ToManyField, ToOneField

__all__ = [
    "GraphQLASTWalker",
]


class GraphQLASTWalker:  # noqa: PLR0904
    """Class for walking the GraphQL AST and handling the different nodes."""

    def __init__(self, info: GQLInfo, model: type[Model]) -> None:
        self.info = info
        self.model = model

    def run(self) -> None:
        field_type = self.info.parent_type
        field_node = self.info.field_nodes[0]
        self.handle_query_class(field_type, field_node)

    def handle_query_class(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        field_type: GraphQLCompositeType = self.get_field_type(parent_type, field_node)  # type: ignore[assignment]
        if field_node.selection_set is not None:
            self.handle_selections(field_type, field_node.selection_set.selections)

    def handle_selections(self, parent_type: GraphQLCompositeType, selections: Selections) -> None:
        if isinstance(parent_type, GraphQLInterfaceType | GraphQLUnionType):
            self.handle_abstract_type(parent_type, selections)
            return

        self.handle_object_type(parent_type, selections)  # type: ignore[arg-type]

    def handle_abstract_type(self, parent_type: GraphQLAbstractType, selections: Selections) -> None:
        if is_node_interface(parent_type):
            self.handle_node_interface(parent_type, selections)

        results = self.flatten_abstract_type_selections(selections)
        types_with_fragments: set[str] = set()

        for inline_fragment in results.inline_fragments:
            if should_skip_node(inline_fragment, self.info.variable_values):
                continue

            fragment_name = inline_fragment.type_condition.name.value
            types_with_fragments.add(fragment_name)

            fragment_type: GraphQLObjectType = self.info.schema.get_type(fragment_name)  # type: ignore[assignment]

            fragment_model = self.get_model(fragment_type)
            if fragment_model is None:  # pragma: no cover
                continue

            # Abstract types are only optimized in the top-level of the query.
            # In this case, we only optimize the fragment for the model that was set
            # in Optimizer initialization. Resolvers should run optimizer
            # for each returned concrete type separately.
            if fragment_model != self.model:
                continue

            fragment_selections = itertools.chain(inline_fragment.selection_set.selections, results.field_nodes)
            self.handle_selections(fragment_type, fragment_selections)

        # If there is no inline fragment for some concrete implementation of an interface,
        # but some fields have been selected from the interface, we still needs to fetch
        # the concrete implementations with the interface fields selected.
        if isinstance(parent_type, GraphQLInterfaceType) and results.field_nodes:
            undine_interface = get_undine_interface_type(parent_type)
            if undine_interface is None:
                return

            types_without_fragments = (
                query_type.__schema_name__
                for query_type in undine_interface.__concrete_implementations__()
                if query_type.__schema_name__ not in types_with_fragments
            )

            for fragment_name in types_without_fragments:
                fragment_type = self.info.schema.get_type(fragment_name)  # type: ignore[assignment]

                fragment_model = self.get_model(fragment_type)
                if fragment_model is None:  # pragma: no cover
                    continue

                if fragment_model != self.model:
                    continue

                self.handle_selections(fragment_type, results.field_nodes)

    def handle_node_interface(self, parent_type: GraphQLInterfaceType, selections: Selections) -> None: ...

    def handle_object_type(self, parent_type: GraphQLObjectType, selections: ObjectSelections) -> None:
        for selection in selections:
            if should_skip_node(selection, self.info.variable_values):
                continue

            if is_typename_metafield(selection):
                self.handle_typename_metafield(parent_type, selection)
                continue

            if isinstance(selection, FieldNode):
                with self.with_child_info(parent_type, selection):
                    self.handle_field_node(parent_type, selection)

            elif isinstance(selection, FragmentSpreadNode):
                fragment_definition = self.get_fragment_def(selection)
                fragment_selections: ObjectSelections = fragment_definition.selection_set.selections  # type: ignore[assignment]
                self.handle_object_type(parent_type, fragment_selections)

            else:  # pragma: no cover
                msg = f"Unhandled object selection node: '{selection}'"
                raise GraphQLOptimizerError(msg)

    def handle_field_node(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        if is_connection(parent_type):
            self.handle_connection(parent_type, field_node)
            return

        if is_edge(parent_type):
            self.handle_edge_field(parent_type, field_node)
            return

        if is_page_info(parent_type):
            self.handle_page_info_field(parent_type, field_node)
            return

        field_model = self.get_model(parent_type)
        if field_model is None:  # pragma: no cover
            return

        with self.use_model(field_model):
            self.handle_model_field(parent_type, field_node)

    def handle_typename_metafield(self, parent_type: GraphQLCompositeType, field_node: FieldNode) -> None: ...

    def handle_connection(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        field_type: GraphQLObjectType = self.get_field_type(parent_type, field_node)  # type: ignore[assignment]

        if field_node.name.value == undine_settings.TOTAL_COUNT_PARAM_NAME:
            self.handle_total_count(field_type, field_node)  # type: ignore[arg-type]
            return

        if field_node.selection_set is not None:
            self.handle_selections(field_type, field_node.selection_set.selections)

    def handle_edge_field(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        field_type: GraphQLObjectType = self.get_field_type(parent_type, field_node)  # type: ignore[assignment]

        if field_node.selection_set is not None:
            self.handle_selections(field_type, field_node.selection_set.selections)

    def handle_page_info_field(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None: ...

    def handle_total_count(self, scalar: GraphQLScalarType, field_node: FieldNode) -> None: ...

    def handle_model_field(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> None:
        field_name = to_snake_case(field_node.name.value)

        try:
            field: ModelField | None = get_model_field(model=self.model, lookup=field_name)
        except ModelFieldError:
            field = None

        if field is None:
            self.handle_custom_field(parent_type, field_node)
            return

        if not field.is_relation or is_relation_id(field, field_node):
            self.handle_normal_field(parent_type, field_node, field)  # type: ignore[arg-type]
            return

        if is_generic_foreign_key(field):
            self.handle_generic_foreign_key(parent_type, field_node, field)
            return

        if is_to_one(field):
            self.handle_to_one_field(parent_type, field_node, field)
            return

        if is_to_many(field):
            self.handle_to_many_field(parent_type, field_node, field)
            return

        msg = f"Unhandled field: '{field.name}'"  # pragma: no cover
        raise GraphQLOptimizerError(msg)  # pragma: no cover

    def handle_custom_field(
        self,
        parent_type: GraphQLObjectType,
        field_node: FieldNode,
    ) -> None: ...

    def handle_normal_field(
        self,
        parent_type: GraphQLObjectType,
        field_node: FieldNode,
        field: Field,
    ) -> None: ...

    def handle_to_one_field(
        self,
        parent_type: GraphQLObjectType,
        field_node: FieldNode,
        related_field: ToOneField,
    ) -> None:
        field_type: GraphQLObjectType = self.get_field_type(parent_type, field_node)  # type: ignore[assignment]
        if field_node.selection_set is not None:
            self.handle_selections(field_type, field_node.selection_set.selections)

    def handle_to_many_field(
        self,
        parent_type: GraphQLObjectType,
        field_node: FieldNode,
        related_field: ToManyField,
    ) -> None:
        field_type: GraphQLObjectType = self.get_field_type(parent_type, field_node)  # type: ignore[assignment]
        if field_node.selection_set is not None:
            self.handle_selections(field_type, field_node.selection_set.selections)

    def handle_generic_foreign_key(
        self,
        parent_type: GraphQLObjectType,
        field_node: FieldNode,
        related_field: GenericForeignKey,
    ) -> None:
        field_type: GraphQLUnionType = self.get_field_type(parent_type, field_node)  # type: ignore[assignment]
        if field_node.selection_set is not None:
            self.handle_selections(field_type, field_node.selection_set.selections)

    def get_model(self, object_type: GraphQLObjectType) -> type[Model] | None:
        query_type = get_undine_query_type(object_type)
        if query_type is None:
            return None
        return query_type.__model__

    def get_field_type(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> GraphQLNamedOutputType:
        graphql_field = get_field_def(self.info.schema, parent_type, field_node)
        return get_underlying_type(graphql_field.type)  # type: ignore[return-value,type-var]

    def get_fragment_def(self, fragment_spread: FragmentSpreadNode) -> FragmentDefinitionNode:
        fragment_name = fragment_spread.name.value
        return self.info.fragments[fragment_name]

    def flatten_abstract_type_selections(self, selections: Selections) -> AbstractSelections:
        results = AbstractSelections()

        for selection in selections:
            if isinstance(selection, FieldNode):
                results.field_nodes.append(selection)

            elif isinstance(selection, InlineFragmentNode):
                results.inline_fragments.append(selection)

            elif isinstance(selection, FragmentSpreadNode):
                fragment_definition = self.get_fragment_def(selection)
                fragment_results = self.flatten_abstract_type_selections(fragment_definition.selection_set.selections)
                results.field_nodes += fragment_results.field_nodes
                results.inline_fragments += fragment_results.inline_fragments

        return results

    @contextmanager
    def use_model(self, model: type[Model]) -> Generator[None, Any, None]:
        orig_model = self.model
        try:
            self.model = model
            yield
        finally:
            self.model = orig_model

    @contextmanager
    def with_child_info(self, parent_type: GraphQLObjectType, field_node: FieldNode) -> Generator[None, None, None]:
        parent_info = self.info

        field_name = field_node.name.value
        field_def = get_field_def(self.info.schema, parent_type, field_node)
        key = get_field_entry_key(field_node)
        path = self.info.path.add_key(key, parent_type.name)

        info = GraphQLResolveInfo(
            field_name=field_name,
            field_nodes=[field_node],
            return_type=field_def.type,
            parent_type=parent_type,
            path=path,
            schema=self.info.schema,
            fragments=self.info.fragments,
            root_value=self.info.root_value,
            operation=self.info.operation,
            variable_values=self.info.variable_values,
            context=self.info.context,
            is_awaitable=self.info.is_awaitable,
        )

        try:
            self.info = info  # type: ignore[assignment]
            yield
        finally:
            self.info = parent_info
