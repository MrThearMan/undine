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
    "MaxAliasCountRule",
]


class MaxAliasCountRule(ValidationRule):
    """Validates that the number of aliases in a GraphQL query does not exceed the maximum allowed."""

    def __init__(self, context: ValidationContext) -> None:
        super().__init__(context)
        self.visited_fragments: set[str] = set()

    def enter_operation_definition(self, node: OperationDefinitionNode, *_args: Any) -> VisitorAction:
        alias_count = self.count_aliases(node)

        if alias_count > undine_settings.MAX_ALLOWED_ALIASES:
            msg = (
                f"Operation has more than {undine_settings.MAX_ALLOWED_ALIASES} aliases, "
                f"which exceeds the maximum allowed."
            )
            error = GraphQLError(msg, node)
            self.context.report_error(error)
            return self.BREAK

        return self.IDLE

    def count_aliases(self, node: ExecutableDefinitionNode | SelectionNode) -> int:  # noqa: C901,PLR0912
        alias_count: int = 0

        match node:
            case FieldNode():
                if node.alias is not None:
                    alias_count += 1

                if node.selection_set is not None:
                    for selection in node.selection_set.selections:
                        alias_count += self.count_aliases(selection)

            case OperationDefinitionNode():
                for selection in node.selection_set.selections:
                    alias_count += self.count_aliases(selection)

            case InlineFragmentNode():
                for selection in node.selection_set.selections:
                    alias_count += self.count_aliases(selection)

            case FragmentSpreadNode():
                if node.name.value not in self.visited_fragments:
                    self.visited_fragments.add(node.name.value)
                    fragment = self.context.get_fragment(node.name.value)
                    if fragment is not None:
                        alias_count += self.count_aliases(fragment)

            case FragmentDefinitionNode():
                for selection in node.selection_set.selections:
                    alias_count += self.count_aliases(selection)

        return alias_count
