from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import GraphQLError, ValidationRule
from graphql.language import ast

from undine.utils.graphql.undine_extensions import (
    get_undine_calculation_argument,
    get_undine_directive,
    get_undine_directive_argument,
    get_undine_filter,
    get_undine_filterset,
    get_undine_input,
    get_undine_mutation_type,
    get_undine_order,
    get_undine_orderset,
)
from undine.utils.graphql.utils import get_underlying_type
from undine.utils.visibility import is_visible

if TYPE_CHECKING:
    from collections.abc import Generator

    from graphql import (
        ArgumentNode,
        FieldNode,
        GraphQLCompositeType,
        GraphQLDirective,
        GraphQLEnumType,
        GraphQLInputObjectType,
        GraphQLInputType,
        VisitorAction,
    )
    from graphql.language.visitor import VisitorActionEnum

    from undine.execution import UndineValidationContext
    from undine.typing import DjangoRequestProtocol


__all__ = [
    "VisibilityRule",
]


class VisibilityRule(ValidationRule):
    """Validates that fields that are not visible to the user are not queried."""

    context: UndineValidationContext

    @property
    def request(self) -> DjangoRequestProtocol:
        # This rule is only used in request contexts
        return self.context.request  # type: ignore[return-value]

    # Entry hooks

    def enter_field(self, node: ast.FieldNode, *args: Any) -> VisitorAction:
        graphql_field = self.context.get_field_def()
        if not graphql_field:
            return None

        parent_type = self.context.get_parent_type()
        if not parent_type:  # pragma: no cover
            return None

        if not is_visible(graphql_field, self.request):
            self.report_field_error(parent_type, node)
            return self.BREAK

        for arg in graphql_field.args.values():
            arg_type = get_underlying_type(arg.type)

            # MutationType entrypoints are hidden if the input type is hidden
            if get_undine_mutation_type(arg_type) is not None and not is_visible(arg_type, self.request):
                self.report_field_error(parent_type, node)
                return self.BREAK

        return None

    def enter_argument(self, node: ast.ArgumentNode, *args: Any) -> VisitorAction:  # noqa: PLR0911
        # Get last ancestor, which is the field node containing the argument.
        field_node: FieldNode = args[-1][-1]

        graphql_input_type = self.context.get_input_type()
        if graphql_input_type is None:
            return None

        node_value = node.value
        if isinstance(node_value, ast.VariableNode):
            node_value = self.context.variable_as_ast(node_value.name.value, graphql_input_type)  # type: ignore[assignment]
            if node_value is None:
                return None

        graphql_input_type = get_underlying_type(graphql_input_type)

        undine_filterset = get_undine_filterset(graphql_input_type)
        if undine_filterset is not None:
            object_value_node: ast.ObjectValueNode = node_value  # type: ignore[assignment]
            return self.handle_filterset(field_node, node, object_value_node, graphql_input_type)

        undine_orderset = get_undine_orderset(graphql_input_type)
        if undine_orderset is not None:
            orderset_node_value: ast.EnumValueNode | ast.ListValueNode = node_value  # type: ignore[assignment]
            return self.handle_orderset(field_node, node, orderset_node_value, graphql_input_type)

        undine_mutation_type = get_undine_mutation_type(graphql_input_type)
        if undine_mutation_type is not None:
            mutation_node_value: ast.ObjectValueNode | ast.ListValueNode = node_value  # type: ignore[assignment]
            return self.handle_mutation_type(field_node, node, mutation_node_value, graphql_input_type)

        graphql_directive = self.context.get_directive()
        if graphql_directive is not None:
            return self.handle_directive_argument(graphql_directive, node)

        graphql_argument = self.context.get_argument()
        if graphql_argument is None:  # pragma: no cover
            return None

        if get_undine_calculation_argument(graphql_argument) is not None:
            parent_type = self.context.get_parent_type()
            if not parent_type:  # pragma: no cover
                return None

            if not is_visible(graphql_argument, self.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return self.BREAK

            return None

        return None

    def enter_named_type(self, node: ast.NamedTypeNode, *args: Any) -> VisitorAction:
        graphql_type = self.context.get_type()
        if graphql_type is None:
            # Handled by `graphql.validation.rules.known_type_names.KnownTypeNamesRule`
            return None

        underlying = get_underlying_type(graphql_type)
        if not is_visible(underlying, self.request):
            self.report_type_error(underlying, node)
            return self.BREAK

        return None

    def enter_directive(self, node: ast.DirectiveNode, *args: Any) -> VisitorAction:
        graphql_directive = self.context.get_directive()
        if graphql_directive is None:
            return None

        if get_undine_directive(graphql_directive) is None:
            return None

        if not is_visible(graphql_directive, self.request):
            self.report_directive_error(graphql_directive, node)
            return self.BREAK

        return None

    # handle undine types

    def handle_filterset(
        self,
        node: FieldNode,
        argument_node: ArgumentNode,
        object_value_node: ast.ObjectValueNode,
        graphql_input_type: GraphQLInputObjectType,
    ) -> VisitorActionEnum | None:
        parent_type = self.context.get_parent_type()
        if not parent_type:  # pragma: no cover
            return None

        if not is_visible(graphql_input_type, self.request):
            self.report_field_argument_error(parent_type, node, argument_node)
            return self.BREAK

        action: VisitorAction = None
        for field_node in self.iter_filters(object_value_node.fields[0], graphql_input_type):
            input_field = graphql_input_type.fields.get(field_node.name.value)
            if input_field is None:
                continue

            if get_undine_filter(input_field) is None:
                continue

            if not is_visible(input_field, self.request):
                self.report_input_field_error(graphql_input_type, field_node)
                action = self.BREAK

        return action

    def handle_orderset(
        self,
        node: FieldNode,
        argument_node: ArgumentNode,
        enum_value_node: ast.EnumValueNode | ast.ListValueNode,
        graphql_enum_type: GraphQLEnumType,
    ) -> VisitorActionEnum | None:
        parent_type = self.context.get_parent_type()
        if not parent_type:  # pragma: no cover
            return None

        if not is_visible(graphql_enum_type, self.request):
            self.report_field_argument_error(parent_type, node, argument_node)
            return self.BREAK

        action: VisitorAction = None
        for value_node in self.iter_orders(enum_value_node, graphql_enum_type):
            enum_value = graphql_enum_type.values.get(value_node.value)
            if enum_value is None:
                continue

            if get_undine_order(enum_value) is None:  # pragma: no cover
                continue

            if not is_visible(enum_value, self.request):
                self.report_enum_error(graphql_enum_type, value_node)
                action = self.BREAK

        return action

    def handle_mutation_type(
        self,
        node: FieldNode,
        argument_node: ArgumentNode,
        mutation_node_value: ast.ObjectValueNode | ast.ListValueNode,
        graphql_input_type: GraphQLInputObjectType,
    ) -> VisitorActionEnum | None:
        parent_type = self.context.get_parent_type()
        if not parent_type:  # pragma: no cover
            return None

        if not is_visible(graphql_input_type, self.request):  # pragma: no cover
            self.report_field_argument_error(parent_type, node, argument_node)
            return self.BREAK

        action: VisitorAction = None
        for field_node in self.iter_inputs(mutation_node_value, graphql_input_type):
            input_field = graphql_input_type.fields.get(field_node.name.value)
            if input_field is None:
                continue

            if get_undine_input(input_field) is None:  # pragma: no cover
                continue

            if not is_visible(input_field, self.request):
                self.report_input_field_error(graphql_input_type, field_node)
                action = self.BREAK

        return action

    def handle_directive_argument(
        self,
        directive_type: GraphQLDirective,
        node: ast.ArgumentNode,
    ) -> VisitorAction:
        arg = directive_type.args.get(node.name.value)
        if arg is None:  # pragma: no cover
            return None

        if get_undine_directive_argument(arg) is None:
            return None

        if not is_visible(arg, self.request):
            self.report_directive_argument_error(directive_type, node)
            return self.BREAK

        return None

    # Report errors

    def report_type_error(
        self,
        parent_type: GraphQLCompositeType,
        node: ast.NamedTypeNode,
    ) -> None:
        # This type is invisible so treat is as if it doesn't exist.
        # Do not include suggestions, since they might include types that are not visible.
        msg = f"Unknown type '{node.name.value}'."
        self.report_error(GraphQLError(msg, node))

    def report_field_error(
        self,
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> None:
        # This field is invisible so treat is as if it doesn't exist.
        # Do not include suggestions, since they might include fields that are not visible.
        msg = f"Cannot query field '{field_node.name.value}' on type '{parent_type}'."
        self.report_error(GraphQLError(msg, nodes=field_node))

    def report_field_argument_error(
        self,
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
        arg_node: ast.ArgumentNode,
    ) -> None:
        # This argument is invisible so treat is as if it doesn't exist.
        # Do not include suggestions, since they might include argument that are not visible.
        msg = f"Unknown argument '{arg_node.name.value}' on field '{parent_type}.{field_node.name.value}'."
        self.report_error(GraphQLError(msg, nodes=arg_node))

    def report_directive_argument_error(
        self,
        parent_type: GraphQLDirective,
        arg_node: ast.ArgumentNode,
    ) -> None:
        # This argument is invisible so treat is as if it doesn't exist.
        # Do not include suggestions, since they might include argument that are not visible.
        msg = f"Unknown argument '{arg_node.name.value}' on directive '{parent_type}'."
        self.report_error(GraphQLError(msg, nodes=arg_node))

    def report_input_field_error(
        self,
        parent_type: GraphQLInputObjectType,
        object_field_node: ast.ObjectFieldNode,
    ) -> None:
        # This argument is invisible so treat is as if it doesn't exist.
        # Do not include suggestions, since they might include arguments that are not visible.
        msg = f"Field '{object_field_node.name.value}' is not defined by type '{parent_type.name}'."
        self.report_error(GraphQLError(msg, nodes=object_field_node))

    def report_enum_error(
        self,
        parent_type: GraphQLEnumType,
        enum_value_node: ast.EnumValueNode,
    ) -> None:
        # This enum value is invisible so treat is as if it doesn't exist.
        # Do not include suggestions, since they might include values that are not visible.
        msg = f"Value '{enum_value_node.value}' does not exist in '{parent_type.name}' enum."
        self.report_error(GraphQLError(msg, nodes=enum_value_node))

    def report_directive_error(
        self,
        parent_type: GraphQLDirective,
        directive_node: ast.DirectiveNode,
    ) -> None:
        # This directive is invisible so treat is as if it doesn't exist.
        # Do not include suggestions, since they might include directives that are not visible.
        msg = f"Unknown directive '@{directive_node.name.value}'."
        self.report_error(GraphQLError(msg, nodes=directive_node))

    # Helpers

    def iter_filters(
        self,
        node: ast.ObjectFieldNode,
        input_type: GraphQLInputType,
    ) -> Generator[ast.ObjectFieldNode, None, None]:
        node_value = node.value

        if node.name.value in {"AND", "OR", "XOR", "NOT"} and isinstance(node_value, ast.ObjectValueNode):
            for sub_node in node_value.fields:
                field_type = input_type.fields[sub_node.name.value].type  # type: ignore[union-attr]
                yield from self.iter_filters(sub_node, field_type)

        elif isinstance(node_value, ast.VariableNode):
            input_field = input_type.fields.get(node_value.name.value)  # type: ignore[union-attr]
            if input_field is not None:
                value_node = self.context.variable_as_ast(node_value.name.value, input_field.type)
                if value_node is not None:
                    yield ast.ObjectFieldNode(name=node_value.name, value=value_node)

        else:
            yield node

    def iter_orders(
        self,
        node: ast.EnumValueNode | ast.ListValueNode,
        graphql_enum_type: GraphQLEnumType,
    ) -> Generator[ast.EnumValueNode, None, None]:
        if isinstance(node, ast.EnumValueNode):
            node = ast.ListValueNode(values=[node])

        for value_node in node.values:
            if isinstance(value_node, ast.VariableNode):
                resolved = self.context.variable_as_ast(value_node.name.value, graphql_enum_type)
                if isinstance(resolved, ast.EnumValueNode):
                    yield resolved
            else:
                yield value_node  # type: ignore[misc]

    def iter_inputs(
        self,
        node: ast.ObjectValueNode | ast.ListValueNode,
        graphql_input_type: GraphQLInputType,
    ) -> Generator[ast.ObjectFieldNode, None, None]:
        if isinstance(node, ast.ObjectValueNode):
            node = ast.ListValueNode(values=[node])

        for item in node.values:
            if isinstance(item, ast.VariableNode):
                resolved = self.context.variable_as_ast(item.name.value, graphql_input_type)
                if isinstance(resolved, ast.ObjectValueNode):
                    yield from resolved.fields
            else:
                yield from item.fields  # type: ignore[attr-defined]
