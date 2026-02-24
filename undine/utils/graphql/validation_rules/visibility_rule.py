from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import GraphQLError, ValidationRule, ast_from_value
from graphql.language import ast

from undine import InterfaceType, MutationType, QueryType, UnionType
from undine.relay import Connection
from undine.utils.graphql.undine_extensions import (
    get_undine_calculation_argument,
    get_undine_directive,
    get_undine_directive_argument,
    get_undine_entrypoint,
    get_undine_field,
    get_undine_filter,
    get_undine_filterset,
    get_undine_input,
    get_undine_interface_field,
    get_undine_interface_type,
    get_undine_mutation_type,
    get_undine_order,
    get_undine_orderset,
    get_undine_query_type,
    get_undine_union_type,
)
from undine.utils.graphql.utils import get_underlying_type
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from collections.abc import Generator

    from graphql import (
        FieldNode,
        GraphQLCompositeType,
        GraphQLDirective,
        GraphQLEnumType,
        GraphQLInputObjectType,
        GraphQLInputType,
        VisitorAction,
    )

    from undine import Entrypoint, Field, InterfaceField
    from undine.execution import UndineValidationContext


__all__ = [
    "VisibilityRule",
]


class VisibilityRule(ValidationRule):  # noqa: PLR0904
    """Validates that fields that are not visible to the user are not queried."""

    context: UndineValidationContext

    # Entry hooks

    def enter_field(self, node: ast.FieldNode, *args: Any) -> VisitorAction:
        parent_type = self.context.get_parent_type()
        if not parent_type:
            return None

        graphql_field = self.context.get_field_def()
        if not graphql_field:
            return None

        undine_entrypoint = get_undine_entrypoint(graphql_field)
        if undine_entrypoint is not None:
            return self.handle_entrypoint(undine_entrypoint, parent_type, node)

        undine_field = get_undine_field(graphql_field)
        if undine_field is not None:
            return self.handle_field(undine_field, parent_type, node)

        undine_interface_field = get_undine_interface_field(graphql_field)
        if undine_interface_field is not None:
            return self.handle_interface_field(undine_interface_field, parent_type, node)

        return None

    def enter_argument(self, node: ast.ArgumentNode, *args: Any) -> VisitorAction:  # noqa: PLR0911,PLR0912,C901
        # Get last ancestor, which is the field node containing the argument.
        field_node: FieldNode = args[-1][-1]

        graphql_argument = self.context.get_argument()
        if graphql_argument is None:
            return None

        parent_type = self.context.get_parent_type()
        if not parent_type:
            return None

        graphql_input_type = self.context.get_input_type()
        if graphql_input_type is None:
            return None

        node_value = node.value
        if isinstance(node_value, ast.VariableNode):
            node_value = self.context.variable_as_ast(node_value.name.value, graphql_input_type)
            if node_value is None:
                return None

        while hasattr(graphql_input_type, "of_type"):
            graphql_input_type = graphql_input_type.of_type

        undine_filterset = get_undine_filterset(graphql_input_type)
        if undine_filterset is not None:
            if not undine_filterset.__is_visible__(self.context.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return self.BREAK

            filterset_node_value: ast.ObjectValueNode = node_value  # type: ignore[assignment]
            return self.handle_filters(graphql_input_type, filterset_node_value)

        undine_orderset = get_undine_orderset(graphql_input_type)
        if undine_orderset is not None:
            if not undine_orderset.__is_visible__(self.context.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return self.BREAK

            orderset_node_value: ast.EnumValueNode | ast.ListValueNode = node_value  # type: ignore[assignment]
            return self.handle_orders(graphql_input_type, orderset_node_value)

        undine_mutation_type = get_undine_mutation_type(graphql_input_type)
        if undine_mutation_type is not None:
            if not undine_mutation_type.__is_visible__(self.context.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return self.BREAK

            mutation_node_value: ast.ObjectValueNode | ast.ListValueNode = node_value  # type: ignore[assignment]
            return self.handle_inputs(graphql_input_type, mutation_node_value)

        undine_calculation_arg = get_undine_calculation_argument(graphql_argument)
        if undine_calculation_arg is not None:
            if undine_calculation_arg.visible_func is None:
                return None

            if not undine_calculation_arg.visible_func(undine_calculation_arg, self.context.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return self.BREAK

            return None

        graphql_directive = self.context.get_directive()
        if graphql_directive is not None:
            return self.handle_directive_arguments(graphql_directive, node)

        return None

    def enter_named_type(self, node: ast.NamedTypeNode, *args: Any) -> VisitorAction:
        graphql_type = self.context.get_type()
        if graphql_type is None:
            # Handled by `graphql.validation.rules.known_type_names.KnownTypeNamesRule`
            return None

        undine_query_type = get_undine_query_type(graphql_type)
        if undine_query_type is not None:
            if not undine_query_type.__is_visible__(self.context.request):
                self.report_type_error(graphql_type, node)
                return self.BREAK

            return None

        undine_interface_type = get_undine_interface_type(graphql_type)
        if undine_interface_type is not None:
            if not undine_interface_type.__is_visible__(self.context.request):
                self.report_type_error(graphql_type, node)
                return self.BREAK

            return None

        undine_union_type = get_undine_union_type(graphql_type)
        if undine_union_type is not None:
            if not undine_union_type.__is_visible__(self.context.request):
                self.report_type_error(graphql_type, node)
                return self.BREAK

            return None

        return None

    def enter_directive(self, node: ast.DirectiveNode, *args: Any) -> VisitorAction:
        graphql_directive = self.context.get_directive()
        if graphql_directive is None:
            return None

        undine_directive = get_undine_directive(graphql_directive)
        if undine_directive is None:
            return None

        if not undine_directive.__is_visible__(self.context.request):
            self.report_directive_error(graphql_directive, node)
            return self.BREAK

        return None

    # handle undine types

    def handle_entrypoint(
        self,
        undine_entrypoint: Entrypoint,
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> VisitorAction:
        if undine_entrypoint.visible_func is not None:
            if not undine_entrypoint.visible_func(undine_entrypoint, self.context.request):
                self.report_field_error(parent_type, field_node)
                return self.BREAK

            return None

        ref = undine_entrypoint.ref

        if isinstance(ref, Connection):
            if ref.query_type is not None:
                ref = ref.query_type
            elif ref.union_type is not None:
                ref = ref.union_type
            elif ref.interface_type is not None:
                ref = ref.interface_type

        if is_subclass(ref, QueryType):
            return self.handle_query_type(ref, parent_type, field_node)

        if is_subclass(ref, MutationType):
            return self.handle_mutation_type(ref, parent_type, field_node)

        if is_subclass(ref, InterfaceType):
            return self.handle_interface_type(ref, parent_type, field_node)

        if is_subclass(ref, UnionType):
            return self.handle_union_type(ref, parent_type, field_node)

        return None

    def handle_field(
        self,
        undine_field: Field,
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> VisitorAction:
        if undine_field.visible_func is not None:
            if not undine_field.visible_func(undine_field, self.context.request):
                self.report_field_error(parent_type, field_node)
                return self.BREAK

            return None

        ref = undine_field.ref

        if isinstance(ref, Connection):
            if ref.query_type is not None:
                ref = ref.query_type
            elif ref.union_type is not None:
                ref = ref.union_type
            elif ref.interface_type is not None:
                ref = ref.interface_type

        if is_subclass(ref, QueryType):
            return self.handle_query_type(ref, parent_type, field_node)

        if is_subclass(ref, MutationType):
            return self.handle_mutation_type(ref, parent_type, field_node)

        if is_subclass(ref, InterfaceType):
            return self.handle_interface_type(ref, parent_type, field_node)

        if is_subclass(ref, UnionType):
            return self.handle_union_type(ref, parent_type, field_node)

        return None

    def handle_interface_field(
        self,
        undine_interface_field: InterfaceField,
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> VisitorAction:
        if undine_interface_field.visible_func is None:
            return None

        if not undine_interface_field.visible_func(undine_interface_field, self.context.request):
            self.report_field_error(parent_type, field_node)
            return self.BREAK

        return None

    def handle_query_type(
        self,
        ref: type[QueryType],
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> VisitorAction:
        if not ref.__is_visible__(self.context.request):
            self.report_field_error(parent_type, field_node)
            return self.BREAK

        return None

    def handle_mutation_type(
        self,
        ref: type[MutationType],
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> VisitorAction:
        if not ref.__is_visible__(self.context.request):
            self.report_field_error(parent_type, field_node)
            return self.BREAK

        output_type = ref.__output_type__()
        query_type = get_undine_query_type(output_type)
        if query_type is not None and not query_type.__is_visible__(self.context.request):
            self.report_field_error(parent_type, field_node)
            return self.BREAK

        return None

    def handle_interface_type(
        self,
        ref: type[InterfaceType],
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> VisitorAction:
        if not ref.__is_visible__(self.context.request):
            self.report_field_error(parent_type, field_node)
            return self.BREAK

        return None

    def handle_union_type(
        self,
        ref: type[UnionType],
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> VisitorAction:
        if not ref.__is_visible__(self.context.request):
            self.report_field_error(parent_type, field_node)
            return self.BREAK

        return None

    def handle_filters(
        self,
        input_type: GraphQLInputObjectType,
        node: ast.ObjectValueNode,
    ) -> VisitorAction:
        action: VisitorAction = None
        for field_node in self.flatten_filters(node.fields[0], input_type):
            if field_node is None:
                continue

            filter_name = field_node.name.value
            input_field = input_type.fields.get(filter_name)
            if input_field is None:
                continue

            undine_filter = get_undine_filter(input_field)
            if undine_filter is None:
                continue

            if undine_filter.visible_func is None:
                continue

            if not undine_filter.visible_func(undine_filter, self.context.request):
                self.report_input_field_error(input_type, field_node)
                action = self.BREAK

        return action

    def handle_orders(
        self,
        enum_type: GraphQLEnumType,
        node: ast.ListValueNode | ast.EnumValueNode,
    ) -> VisitorAction:
        action: VisitorAction = None

        if isinstance(node, ast.EnumValueNode):
            node = ast.ListValueNode(values=[node])

        value_node: ast.EnumValueNode | ast.VariableNode
        for value_node in node.values:
            if isinstance(value_node, ast.VariableNode):
                value_node = self.context.variable_as_ast(value_node.name.value, enum_type)  # type: ignore[assignment]  # noqa: PLW2901
                if not isinstance(value_node, ast.EnumValueNode):
                    continue

            enum_name = value_node.value
            enum_value = enum_type.values.get(enum_name)
            if enum_value is None:
                continue

            undine_order = get_undine_order(enum_value)
            if undine_order is None:
                continue

            if undine_order.visible_func is None:
                continue

            if not undine_order.visible_func(undine_order, self.context.request):
                self.report_enum_error(enum_type, value_node)
                action = self.BREAK

        return action

    def handle_inputs(
        self,
        input_type: GraphQLInputObjectType,
        node: ast.ObjectValueNode | ast.ListValueNode,
    ) -> VisitorAction:
        action: VisitorAction = None

        if isinstance(node, ast.ObjectValueNode):
            node = ast.ListValueNode(values=[node])

        item: ast.ObjectValueNode | ast.VariableNode
        for item in node.values:
            if isinstance(item, ast.VariableNode):
                item = self.context.variable_as_ast(item.name.value, input_type)  # type: ignore[assignment]  # noqa: PLW2901
                if item is None:
                    continue

            for field_node in item.fields:
                input_name = field_node.name.value
                input_field = input_type.fields.get(input_name)
                if input_field is None:
                    continue

                undine_input = get_undine_input(input_field)
                if undine_input is None:
                    continue

                if undine_input.visible_func is None:
                    undine_input_type: GraphQLInputObjectType = get_underlying_type(input_field.type)  # type: ignore[assignment]
                    undine_mutation_type = get_undine_mutation_type(undine_input_type)
                    if undine_mutation_type is None:
                        continue

                    if not undine_mutation_type.__is_visible__(self.context.request):
                        self.report_input_field_error(input_type, field_node)
                        action = self.BREAK

                    continue

                if not undine_input.visible_func(undine_input, self.context.request):
                    self.report_input_field_error(input_type, field_node)
                    action = self.BREAK

        return action

    def handle_directive_arguments(
        self,
        directive_type: GraphQLDirective,
        node: ast.ArgumentNode,
    ) -> VisitorAction:
        arg = directive_type.args.get(node.name.value)
        if arg is None:
            return None

        undine_directive_arg = get_undine_directive_argument(arg)
        if undine_directive_arg is None:
            return None

        if undine_directive_arg.visible_func is None:
            return None

        if not undine_directive_arg.visible_func(undine_directive_arg, self.context.request):
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

    def flatten_filters(
        self,
        node: ast.ObjectFieldNode,
        input_type: GraphQLInputType,
    ) -> Generator[ast.ObjectFieldNode | None, None, None]:
        node_value = node.value

        if node.name.value in {"AND", "OR", "XOR", "NOT"} and isinstance(node_value, ast.ObjectValueNode):
            for sub_node in node_value.fields:
                field_type = input_type.fields[sub_node.name.value].type
                yield from self.flatten_filters(sub_node, field_type)

        elif isinstance(node_value, ast.VariableNode):
            input_field = input_type.fields.get(node_value.name.value)
            if input_field is None:
                yield None
            else:
                value_node = ast_from_value(self.context.variables[node_value.name.value], input_field.type)
                yield ast.ObjectFieldNode(name=node_value.name, value=value_node)

        else:
            yield node
