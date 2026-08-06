from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import FieldNode, FragmentSpreadNode, GraphQLError, GraphQLObjectType, InlineFragmentNode, ValidationRule

from undine.settings import undine_settings
from undine.utils.graphql.utils import get_underlying_type, is_list_of_composite_type

if TYPE_CHECKING:
    from graphql import (
        GraphQLAbstractType,
        GraphQLCompositeType,
        OperationDefinitionNode,
        SelectionNode,
        ValidationContext,
        VisitorAction,
    )


__all__ = [
    "MaxListNestingDepthRule",
]


class MaxListNestingDepthRule(ValidationRule):
    """
    Validates that to-many relations in a GraphQL query are not nested inside one another too deeply.

    Only fields returning a list of composite types count towards the nesting depth, since to-one
    relations are joined into the same database query and thus don't multiply the number of rows
    returned, whereas each nested to-many relation does.
    """

    def __init__(self, context: ValidationContext) -> None:
        super().__init__(context)
        self.max_depth: int = 0
        self.visited_fragments: set[str] = set()

    def enter_operation_definition(self, node: OperationDefinitionNode, *_args: Any) -> VisitorAction:
        root_type = self.context.get_type()
        if not isinstance(root_type, GraphQLObjectType):
            return self.IDLE

        for selection in node.selection_set.selections:
            self.visited_fragments = set()
            self.handle_selection(root_type, selection, depth=0)

        if self.max_depth > undine_settings.MAX_LIST_NESTING_DEPTH:
            msg = (
                f"List nesting depth of {self.max_depth} exceeds the maximum allowed "
                f"list nesting depth of {undine_settings.MAX_LIST_NESTING_DEPTH}."
            )
            error = GraphQLError(msg, node)
            self.context.report_error(error)
            return self.BREAK

        return self.IDLE

    def handle_selection(self, parent_type: GraphQLCompositeType, selection: SelectionNode, *, depth: int) -> None:
        match selection:
            case FieldNode():
                self.handle_field(parent_type, selection, depth=depth)

            case FragmentSpreadNode():
                self.handle_fragment_spread(parent_type, selection, depth=depth)

            case InlineFragmentNode():  # pragma: no branch
                self.handle_inline_fragment(parent_type, selection, depth=depth)  # type: ignore[arg-type]

    def handle_field(self, parent_type: GraphQLCompositeType, field_node: FieldNode, *, depth: int) -> None:
        # Ignore fields on interfaces, as well as union '__typename'.
        if not isinstance(parent_type, GraphQLObjectType):
            return

        graphql_field = parent_type.fields.get(field_node.name.value)
        if graphql_field is None:
            return

        if is_list_of_composite_type(graphql_field.type):
            depth += 1
            self.max_depth = max(self.max_depth, depth)

        if field_node.selection_set is None:
            return

        field_type: GraphQLObjectType = get_underlying_type(graphql_field.type)

        for selection in field_node.selection_set.selections:
            self.handle_selection(field_type, selection, depth=depth)

    def handle_fragment_spread(
        self,
        parent_type: GraphQLCompositeType,
        fragment_spread: FragmentSpreadNode,
        *,
        depth: int,
    ) -> None:
        fragment_name = fragment_spread.name.value
        # Guard against fragment cycles, which are reported by the 'NoFragmentCyclesRule'.
        if fragment_name in self.visited_fragments:
            return

        fragment = self.context.get_fragment(fragment_name)
        if fragment is None:
            return

        self.visited_fragments.add(fragment_name)

        for selection in fragment.selection_set.selections:
            self.handle_selection(parent_type, selection, depth=depth)

        self.visited_fragments.discard(fragment_name)

    def handle_inline_fragment(
        self,
        parent_type: GraphQLAbstractType,
        inline_fragment: InlineFragmentNode,
        *,
        depth: int,
    ) -> None:
        type_condition = inline_fragment.type_condition
        if type_condition is None:
            for selection in inline_fragment.selection_set.selections:
                self.handle_selection(parent_type, selection, depth=depth)
            return

        fragment_type_name = type_condition.name.value
        fragment_type: GraphQLObjectType = self.context.schema.get_type(fragment_type_name)  # type: ignore[assignment]

        for selection in inline_fragment.selection_set.selections:
            self.handle_selection(fragment_type, selection, depth=depth)
