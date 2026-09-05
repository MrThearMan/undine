from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import (
    FieldNode,
    FragmentSpreadNode,
    GraphQLError,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLUnionType,
    InlineFragmentNode,
    ValidationRule,
)

from undine.settings import undine_settings
from undine.utils.graphql.undine_extensions import get_undine_entrypoint, get_undine_field
from undine.utils.graphql.utils import get_underlying_type, is_typename_metafield

if TYPE_CHECKING:
    from graphql import (
        FragmentDefinitionNode,
        GraphQLAbstractType,
        GraphQLCompositeType,
        OperationDefinitionNode,
        SelectionNode,
        ValidationContext,
        VisitorAction,
    )

    from undine.typing import Selections


__all__ = [
    "MaxComplexityRule",
]


class MaxComplexityRule(ValidationRule):
    """Validates that the complexity of a GraphQL query does not exceed the maximum allowed."""

    def __init__(self, context: ValidationContext) -> None:
        super().__init__(context)
        self.complexity: int = 0
        self.fragments_in_progress: set[str] = set()

    def enter_operation_definition(self, node: OperationDefinitionNode, *_args: Any) -> VisitorAction:
        root_type = self.context.get_type()
        if not isinstance(root_type, GraphQLObjectType):
            return self.IDLE

        visited_fragments: set[str] = set()
        for selection in node.selection_set.selections:
            self.handle_selection(root_type, selection, visited_fragments=visited_fragments)

        if self.complexity > undine_settings.MAX_QUERY_COMPLEXITY:
            msg = (
                f"Query complexity of {self.complexity} exceeds the maximum allowed "
                f"complexity of {undine_settings.MAX_QUERY_COMPLEXITY}."
            )
            error = GraphQLError(msg, node)
            self.context.report_error(error)
            return self.BREAK

        return self.IDLE

    def handle_selection(
        self,
        parent_type: GraphQLCompositeType,
        selection: SelectionNode,
        *,
        visited_fragments: set[str],
    ) -> None:
        match selection:
            case FieldNode():
                self.handle_field(parent_type, selection)

            case FragmentSpreadNode():
                self.handle_fragment_spread(parent_type, selection, visited_fragments=visited_fragments)

            case InlineFragmentNode():  # pragma: no branch
                self.handle_inline_fragment(parent_type, selection, visited_fragments=visited_fragments)  # type: ignore[arg-type]

    def handle_field(self, parent_type: GraphQLCompositeType, field_node: FieldNode) -> None:
        # Ignore fields on interfaces, as well as union '__typename'.
        if not isinstance(parent_type, GraphQLObjectType):
            return

        graphql_field = parent_type.fields.get(field_node.name.value)
        if graphql_field is None:
            return

        undine_entrypoint = get_undine_entrypoint(graphql_field)
        if undine_entrypoint is not None:
            self.complexity += undine_entrypoint.complexity

        undine_field = get_undine_field(graphql_field)
        if undine_field is not None:
            self.complexity += undine_field.complexity

        if field_node.selection_set is None:
            return

        field_type: GraphQLObjectType = get_underlying_type(graphql_field.type)
        selections = field_node.selection_set.selections

        if isinstance(field_type, GraphQLUnionType | GraphQLInterfaceType):
            selected_members = self.get_selected_members(field_type, selections)
            self.complexity += len(selected_members)

        visited_fragments: set[str] = set()
        for selection in selections:
            self.handle_selection(field_type, selection, visited_fragments=visited_fragments)

    def get_selected_members(self, abstract_type: GraphQLAbstractType, selections: Selections) -> set[str]:
        """The members of the abstract type the operation selects fields from. Each one is fetched separately."""
        possible_types = {member_type.name for member_type in self.context.schema.get_possible_types(abstract_type)}
        selected_members: set[str] = set()

        for selection in selections:
            if isinstance(selection, FieldNode):
                # A field on the abstract type itself is selected from every member.
                if not is_typename_metafield(selection):
                    return possible_types
                continue

            fragment: FragmentDefinitionNode | InlineFragmentNode
            if isinstance(selection, FragmentSpreadNode):
                fragment_definition = self.context.get_fragment(selection.name.value)
                if fragment_definition is None:
                    continue

                fragment = fragment_definition
            else:
                fragment = selection  # type: ignore[assignment]

            type_condition = fragment.type_condition
            fragment_selections = fragment.selection_set.selections

            fragment_type = None if type_condition is None else self.context.schema.get_type(type_condition.name.value)

            # A fragment without a type condition, or one on another abstract type,
            # applies to every member the same way the surrounding selections do.
            if not isinstance(fragment_type, GraphQLObjectType):
                selected_members |= self.get_selected_members(abstract_type, fragment_selections)
                continue

            if self.selects_a_field(fragment_selections):
                selected_members.add(fragment_type.name)

        return selected_members

    def selects_a_field(self, selections: Selections) -> bool:
        """Does the operation select anything other than the typename in the given selections?"""
        for selection in selections:
            if isinstance(selection, FieldNode):
                if not is_typename_metafield(selection):
                    return True

            elif isinstance(selection, FragmentSpreadNode):
                fragment = self.context.get_fragment(selection.name.value)
                if fragment is not None and self.selects_a_field(fragment.selection_set.selections):
                    return True

            elif isinstance(selection, InlineFragmentNode) and self.selects_a_field(selection.selection_set.selections):
                return True

        return False

    def handle_fragment_spread(
        self,
        parent_type: GraphQLCompositeType,
        fragment_spread: FragmentSpreadNode,
        *,
        visited_fragments: set[str],
    ) -> None:
        fragment_name = fragment_spread.name.value
        if fragment_name in visited_fragments | self.fragments_in_progress:
            return

        fragment = self.context.get_fragment(fragment_name)
        if fragment is None:
            return

        visited_fragments.add(fragment_name)
        self.fragments_in_progress.add(fragment_name)

        for selection in fragment.selection_set.selections:
            self.handle_selection(parent_type, selection, visited_fragments=visited_fragments)

        self.fragments_in_progress.discard(fragment_name)

    def handle_inline_fragment(
        self,
        parent_type: GraphQLAbstractType,
        inline_fragment: InlineFragmentNode,
        *,
        visited_fragments: set[str],
    ) -> None:
        type_condition = inline_fragment.type_condition
        if type_condition is None:
            for selection in inline_fragment.selection_set.selections:
                self.handle_selection(parent_type, selection, visited_fragments=visited_fragments)
            return

        fragment_type_name = type_condition.name.value
        fragment_type: GraphQLObjectType = self.context.schema.get_type(fragment_type_name)  # type: ignore[assignment]

        for selection in inline_fragment.selection_set.selections:
            self.handle_selection(fragment_type, selection, visited_fragments=visited_fragments)
