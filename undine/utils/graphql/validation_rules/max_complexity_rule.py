from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import FieldNode, FragmentSpreadNode, GraphQLError, GraphQLObjectType, InlineFragmentNode, ValidationRule

from undine.settings import undine_settings
from undine.utils.graphql.undine_extensions import get_undine_field
from undine.utils.graphql.utils import get_underlying_type

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
    "MaxComplexityRule",
]


class MaxComplexityRule(ValidationRule):
    """Validates that the complexity of a GraphQL query does not exceed the maximum allowed."""

    def __init__(self, context: ValidationContext) -> None:
        super().__init__(context)
        self.complexity: int = 0
        self.visited_fragments: set[str] = set()

    def enter_operation_definition(self, node: OperationDefinitionNode, *_args: Any) -> VisitorAction:
        root_type = self.context.get_type()
        if not isinstance(root_type, GraphQLObjectType):
            return self.IDLE

        for selection in node.selection_set.selections:
            self.visited_fragments = set()
            self.handle_selection(root_type, selection)

        if self.complexity > undine_settings.MAX_QUERY_COMPLEXITY:
            msg = (
                f"Query complexity of {self.complexity} exceeds the maximum allowed "
                f"complexity of {undine_settings.MAX_QUERY_COMPLEXITY}."
            )
            error = GraphQLError(msg, node)
            self.context.report_error(error)
            return self.BREAK

        return self.IDLE

    def handle_selection(self, parent_type: GraphQLCompositeType, selection: SelectionNode) -> None:
        match selection:
            case FieldNode():
                self.handle_field(parent_type, selection)

            case FragmentSpreadNode():
                self.handle_fragment_spread(parent_type, selection)

            case InlineFragmentNode():
                self.handle_inline_fragment(parent_type, selection)  # type: ignore[arg-type]

    def handle_field(self, parent_type: GraphQLCompositeType, field_node: FieldNode) -> None:
        # Ignore fields on interfaces, as well as union '__typename'.
        if not isinstance(parent_type, GraphQLObjectType):
            return

        graphql_field = parent_type.fields.get(field_node.name.value)
        if graphql_field is None:
            return

        undine_field = get_undine_field(graphql_field)
        if undine_field is not None:
            self.complexity += undine_field.complexity

        if field_node.selection_set is not None:
            field_type: GraphQLObjectType = get_underlying_type(graphql_field.type)

            for selection in field_node.selection_set.selections:
                self.handle_selection(field_type, selection)

    def handle_fragment_spread(self, parent_type: GraphQLCompositeType, fragment_spread: FragmentSpreadNode) -> None:
        fragment_name = fragment_spread.name.value
        if fragment_name in self.visited_fragments:
            return

        self.visited_fragments.add(fragment_name)

        fragment = self.context.get_fragment(fragment_name)
        if fragment is None:
            return

        for selection in fragment.selection_set.selections:
            self.handle_selection(parent_type, selection)

    def handle_inline_fragment(self, parent_type: GraphQLAbstractType, inline_fragment: InlineFragmentNode) -> None:
        fragment_type_name = inline_fragment.type_condition.name.value
        fragment_type: GraphQLObjectType = self.context.schema.get_type(fragment_type_name)  # type: ignore[assignment]

        for selection in inline_fragment.selection_set.selections:
            self.handle_selection(fragment_type, selection)
