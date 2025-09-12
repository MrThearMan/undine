from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import GraphQLError, ValidationRule
from graphql.language import ast

from undine import InterfaceType, MutationType, QueryType, UnionType
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
    get_undine_mutation_type,
    get_undine_order,
    get_undine_orderset,
    get_undine_query_type,
)
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from collections.abc import Generator

    from graphql import (
        FieldNode,
        GraphQLCompositeType,
        GraphQLDirective,
        GraphQLEnumType,
        GraphQLInputObjectType,
        VisitorAction,
    )

    from undine import Entrypoint, Field, InterfaceField
    from undine.typing import DjangoRequestProtocol


__all__ = [
    "VisibilityRule",
    "get_visibility_rule",
]


def get_visibility_rule(*, request: DjangoRequestProtocol) -> type[VisibilityRule]:
    class RequestVisibilityRule(VisibilityRule, request=request): ...

    return RequestVisibilityRule


class VisibilityRule(ValidationRule):  # noqa: PLR0904
    """Validates that fields that are not visible to the user are not queried."""

    def __init_subclass__(cls, request: DjangoRequestProtocol) -> None:
        cls.request = request

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
            self.handle_entrypoint(undine_entrypoint, parent_type, node)
            return None

        undine_field = get_undine_field(graphql_field)
        if undine_field is not None:
            self.handle_field(undine_field, parent_type, node)
            return None

        undine_interface_field = get_undine_interface_field(graphql_field)
        if undine_interface_field is not None:
            self.handle_interface_field(undine_interface_field, parent_type, node)
            return None

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

        while hasattr(graphql_input_type, "of_type"):
            graphql_input_type = graphql_input_type.of_type

        undine_filterset = get_undine_filterset(graphql_input_type)
        if undine_filterset is not None:
            if not undine_filterset.__is_visible__(self.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return None

            object_value: ast.ObjectValueNode = node.value  # type: ignore[assignment]
            self.handle_filters(graphql_input_type, object_value)
            return None

        undine_orderset = get_undine_orderset(graphql_input_type)
        if undine_orderset is not None:
            if not undine_orderset.__is_visible__(self.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return None

            list_value: ast.ListValueNode = node.value  # type: ignore[assignment]
            self.handle_orders(graphql_input_type, list_value)
            return None

        undine_mutation_type = get_undine_mutation_type(graphql_input_type)
        if undine_mutation_type is not None:
            if not undine_mutation_type.__is_visible__(self.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return None

            input_node: ast.ObjectValueNode = node.value  # type: ignore[assignment]
            self.handle_inputs(graphql_input_type, input_node)
            return None

        undine_calculation_arg = get_undine_calculation_argument(graphql_argument)
        if undine_calculation_arg is not None:
            if undine_calculation_arg.visible_func is None:
                return None

            if not undine_calculation_arg.visible_func(undine_calculation_arg, self.request):
                self.report_field_argument_error(parent_type, field_node, node)
                return None

            return None

        graphql_directive = self.context.get_directive()
        if graphql_directive is not None:
            self.handle_directive_arguments(graphql_directive, node)
            return None

        return None

    def enter_named_type(self, node: ast.NamedTypeNode, *args: Any) -> VisitorAction:
        graphql_type = self.context.get_type()
        if graphql_type is None:
            # Handled by `graphql.validation.rules.known_type_names.KnownTypeNamesRule`
            return None

        # Check that fragment definitions and inline fragments can be used on this type.
        undine_query_type = get_undine_query_type(graphql_type)
        if undine_query_type is not None:
            if not undine_query_type.__is_visible__(self.request):
                self.report_type_error(graphql_type, node)
            return None

        return None

    def enter_directive(self, node: ast.DirectiveNode, *args: Any) -> VisitorAction:
        graphql_directive = self.context.get_directive()
        if graphql_directive is None:
            return None

        undine_directive = get_undine_directive(graphql_directive)
        if undine_directive is None:
            return None

        if not undine_directive.__is_visible__(self.request):
            self.report_directive_error(graphql_directive, node)
            return None

        return None

    # handle undine types

    def handle_entrypoint(
        self,
        undine_entrypoint: Entrypoint,
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> None:
        if undine_entrypoint.visible_func is not None:
            if not undine_entrypoint.visible_func(undine_entrypoint, self.request):
                self.report_field_error(parent_type, field_node)
            return

        ref = undine_entrypoint.ref

        if is_subclass(ref, QueryType):
            self.handle_query_type(ref, parent_type, field_node)

        if is_subclass(ref, MutationType):
            self.handle_mutation_type(ref, parent_type, field_node)

        if is_subclass(ref, InterfaceType):
            self.handle_interface_type(ref, parent_type, field_node)

        if is_subclass(ref, UnionType):
            self.handle_union_type(ref, parent_type, field_node)

    def handle_field(
        self,
        undine_field: Field,
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> None:
        if undine_field.visible_func is not None:
            if not undine_field.visible_func(undine_field, self.request):
                self.report_field_error(parent_type, field_node)
            return

        ref = undine_field.ref

        if is_subclass(ref, QueryType):
            self.handle_query_type(ref, parent_type, field_node)

        if is_subclass(ref, MutationType):
            self.handle_mutation_type(ref, parent_type, field_node)

    def handle_interface_field(
        self,
        undine_interface_field: InterfaceField,
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> None:
        if undine_interface_field.visible_func is None:
            return

        if not undine_interface_field.visible_func(undine_interface_field, self.request):
            self.report_field_error(parent_type, field_node)

    def handle_query_type(
        self,
        ref: type[QueryType],
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> None:
        if not ref.__is_visible__(self.request):
            self.report_field_error(parent_type, field_node)
            return

    def handle_mutation_type(
        self,
        ref: type[MutationType],
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> None:
        if not ref.__is_visible__(self.request):
            self.report_field_error(parent_type, field_node)
            return

        output_type = ref.__output_type__()
        query_type = get_undine_query_type(output_type)
        if query_type is not None and not query_type.__is_visible__(self.request):
            self.report_field_error(parent_type, field_node)
            return

    def handle_interface_type(
        self,
        ref: type[InterfaceType],
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> None:
        if not ref.__is_visible__(self.request):
            self.report_field_error(parent_type, field_node)
            return

    def handle_union_type(
        self,
        ref: type[UnionType],
        parent_type: GraphQLCompositeType,
        field_node: ast.FieldNode,
    ) -> None:
        if not ref.__is_visible__(self.request):
            self.report_field_error(parent_type, field_node)
            return

    def handle_filters(
        self,
        input_type: GraphQLInputObjectType,
        object_value: ast.ObjectValueNode,
    ) -> None:
        for field_node in self.flatten_object_field_nodes(object_value.fields[0]):
            filter_name = field_node.name.value
            input_field = input_type.fields.get(filter_name)
            if input_field is None:
                continue

            undine_filter = get_undine_filter(input_field)
            if undine_filter is None:
                continue

            if undine_filter.visible_func is None:
                continue

            if not undine_filter.visible_func(undine_filter, self.request):
                self.report_input_field_error(input_type, field_node)

    def handle_orders(
        self,
        enum_type: GraphQLEnumType,
        list_value: ast.ListValueNode,
    ) -> None:
        value_node: ast.EnumValueNode
        for value_node in list_value.values:
            enum_name = value_node.value
            enum_value = enum_type.values.get(enum_name)
            if enum_value is None:
                continue

            undine_order = get_undine_order(enum_value)
            if undine_order is None:
                continue

            if undine_order.visible_func is None:
                continue

            if not undine_order.visible_func(undine_order, self.request):
                self.report_enum_error(enum_type, value_node)

    def handle_inputs(
        self,
        input_type: GraphQLInputObjectType,
        object_value: ast.ObjectValueNode,
    ) -> None:
        for field_node in object_value.fields:
            input_name = field_node.name.value
            input_field = input_type.fields.get(input_name)
            if input_field is None:
                continue

            undine_input = get_undine_input(input_field)
            if undine_input is None:
                continue

            if undine_input.visible_func is None:
                continue

            if not undine_input.visible_func(undine_input, self.request):
                self.report_input_field_error(input_type, field_node)

    def handle_directive_arguments(
        self,
        directive_type: GraphQLDirective,
        node: ast.ArgumentNode,
    ) -> None:
        arg = directive_type.args.get(node.name.value)
        if arg is None:
            return

        undine_directive_arg = get_undine_directive_argument(arg)
        if undine_directive_arg is None:
            return

        if undine_directive_arg.visible_func is None:
            return

        if not undine_directive_arg.visible_func(undine_directive_arg, self.request):
            self.report_directive_argument_error(directive_type, node)

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

    def flatten_object_field_nodes(self, node: ast.ObjectFieldNode) -> Generator[ast.ObjectFieldNode, None, None]:
        node_value = node.value
        if isinstance(node_value, ast.ObjectValueNode):
            for sub_node in node_value.fields:
                yield from self.flatten_object_field_nodes(sub_node)
        else:
            yield node
