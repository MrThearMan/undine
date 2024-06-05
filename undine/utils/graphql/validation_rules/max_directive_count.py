from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import (
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    GraphQLError,
    InlineFragmentNode,
    OperationDefinitionNode,
    ValidationRule,
)

from undine.settings import undine_settings

if TYPE_CHECKING:
    from graphql import ExecutableDefinitionNode, SelectionNode, ValidationContext, VisitorAction


__all__ = [
    "MaxDirectiveCountRule",
]


class MaxDirectiveCountRule(ValidationRule):
    """Validates that the number of directives in a GraphQL query does not exceed the maximum allowed."""

    def __init__(self, context: ValidationContext) -> None:
        super().__init__(context)
        self.visited_fragments: set[str] = set()

    def enter_operation_definition(self, node: OperationDefinitionNode, *_args: Any) -> VisitorAction:
        directive_count = self.count_directives(node)

        if directive_count > undine_settings.MAX_ALLOWED_DIRECTIVES:
            msg = (
                f"Operation has more than {undine_settings.MAX_ALLOWED_DIRECTIVES} directives, "
                f"which exceeds the maximum allowed."
            )
            error = GraphQLError(msg, node)
            self.context.report_error(error)
            return self.BREAK

        return self.IDLE

    def count_directives(self, node: ExecutableDefinitionNode | SelectionNode) -> int:  # noqa: C901,PLR0912
        directive_count: int = 0

        match node:
            case FieldNode():
                directive_count += len(node.directives)

                if node.selection_set is not None:
                    for selection in node.selection_set.selections:
                        directive_count += self.count_directives(selection)

            case OperationDefinitionNode():
                for variable_definition in node.variable_definitions or ():
                    directive_count += len(variable_definition.directives)

                directive_count += len(node.directives)

                for selection in node.selection_set.selections:
                    directive_count += self.count_directives(selection)

            case InlineFragmentNode():
                directive_count += len(node.directives)

                for selection in node.selection_set.selections:
                    directive_count += self.count_directives(selection)

            case FragmentSpreadNode():
                directive_count += len(node.directives)

                if node.name.value not in self.visited_fragments:
                    self.visited_fragments.add(node.name.value)
                    fragment = self.context.get_fragment(node.name.value)
                    if fragment is not None:
                        directive_count += self.count_directives(fragment)

            case FragmentDefinitionNode():
                for variable_definition in node.variable_definitions or ():
                    directive_count += len(variable_definition.directives)

                directive_count += len(node.directives)

                for selection in node.selection_set.selections:
                    directive_count += self.count_directives(selection)

        return directive_count
