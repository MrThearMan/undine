from __future__ import annotations

import textwrap
from itertools import chain, starmap
from typing import TYPE_CHECKING

from graphql import (
    DEFAULT_DEPRECATION_REASON,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLUnionType,
    ast_from_value,
    is_specified_directive,
    print_ast,
)
from graphql.language.block_string import is_printable_as_block_string, print_block_string
from graphql.language.print_string import print_string
from graphql.pyutils import inspect
from graphql.utilities.print_schema import is_defined_type

from undine.utils.graphql.undine_extensions import (
    get_undine_calculation_argument,
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
    get_undine_root_type,
    get_undine_scalar,
    get_undine_schema_directives,
    get_undine_union_type,
)
from undine.utils.graphql.validation_rules.one_of_input_object import is_one_of_input_object

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from graphql import (
        GraphQLArgument,
        GraphQLDirective,
        GraphQLEnumValue,
        GraphQLField,
        GraphQLInputField,
        GraphQLNamedType,
        GraphQLSchema,
    )

    from undine.directives import Directive

__all__ = [
    "SDLPrinter",
]


class SDLPrinter:  # noqa: PLR0904
    """Print the given GraphQL schema to GraphQL SDL."""

    @classmethod
    def print_schema(
        cls,
        schema: GraphQLSchema,
        *,
        directive_filter: Callable[[GraphQLDirective], bool] | None = None,
        type_filter: Callable[[GraphQLNamedType], bool] | None = None,
    ) -> str:
        if directive_filter is None:
            directive_filter = cls.default_directive_filter
        if type_filter is None:
            type_filter = cls.default_type_filter

        schema_definition = cls.print_schema_definition(schema)

        directives = (
            cls.print_directive(directive)  # ...
            for directive in schema.directives
            if directive_filter(directive)
        )
        types = (
            cls.print_type(type_)  # ...
            for type_ in schema.type_map.values()
            if type_filter(type_)
        )

        return "\n\n".join(
            chain(
                directives,
                types,
                [schema_definition] if schema_definition else [],
            )
        )

    @classmethod
    def print_schema_definition(cls, schema: GraphQLSchema) -> str:
        root_types: dict[str, str] = {}
        description = cls.print_docstring(schema.description)

        schema_str: str = "schema"
        has_directives = False

        undine_schema_directives = get_undine_schema_directives(schema)
        if undine_schema_directives is not None:
            for directive in undine_schema_directives:
                has_directives = True
                schema_str += cls.print_directive_usage(directive)

        if schema.query_type is not None:
            root_types[schema.query_type.name] = f"  query: {schema.query_type.name}"

        if schema.mutation_type is not None:
            root_types[schema.mutation_type.name] = f"  mutation: {schema.mutation_type.name}"

        if schema.subscription_type is not None:
            root_types[schema.subscription_type.name] = f"  subscription: {schema.subscription_type.name}"

        non_default_root_types = set(root_types) - {"Query", "Mutation", "Subscription"}
        has_default_root_types = not non_default_root_types

        # The schema definition only needs to be printed if its not the default schema definition.
        if not description and (not root_types or has_default_root_types) and not has_directives:
            return ""

        schema_str += cls.print_block(root_types.values())
        if description:
            schema_str = f"{description}\n{schema_str}"

        return schema_str

    @classmethod
    def print_type(cls, named_type: GraphQLNamedType) -> str:
        match named_type:
            case GraphQLScalarType():
                return cls.print_scalar_type(named_type)

            case GraphQLObjectType():
                return cls.print_object_type(named_type)

            case GraphQLInterfaceType():
                return cls.print_interface_type(named_type)

            case GraphQLUnionType():
                return cls.print_union_type(named_type)

            case GraphQLEnumType():
                return cls.print_enum_type(named_type)

            case GraphQLInputObjectType():
                return cls.print_input_object_type(named_type)

            case _:
                msg = f"Unexpected type: {inspect(named_type)}."
                raise TypeError(msg)

    # --- ObjectType --------------------------------------------------------------------------------------

    @classmethod
    def print_object_type(cls, object_type: GraphQLObjectType) -> str:
        object_type_str = f"type {object_type.name}"

        if object_type.interfaces:
            object_type_str += " implements " + " & ".join(interface.name for interface in object_type.interfaces)

        undine_query_type = get_undine_query_type(object_type)
        if undine_query_type is not None:
            for directive in undine_query_type.__directives__:
                object_type_str += cls.print_directive_usage(directive)

        undine_root_type = get_undine_root_type(object_type)
        if undine_root_type is not None:
            for directive in undine_root_type.__directives__:
                object_type_str += cls.print_directive_usage(directive)

        if object_type.fields:
            fields = starmap(cls.print_field, object_type.fields.items())
            object_type_str += cls.print_block(fields)

        description = cls.print_docstring(object_type.description)
        if description:
            object_type_str = f"{description}\n{object_type_str}"

        return object_type_str

    @classmethod
    def print_interface_type(cls, interface_type: GraphQLInterfaceType) -> str:
        interface_type_str = f"interface {interface_type.name}"

        if interface_type.interfaces:
            interface_type_str += " implements " + " & ".join(interface.name for interface in interface_type.interfaces)

        undine_interface = get_undine_interface_type(interface_type)
        if undine_interface is not None:
            for directive in undine_interface.__directives__:
                interface_type_str += cls.print_directive_usage(directive)

        if interface_type.fields:
            fields = starmap(cls.print_field, interface_type.fields.items())
            interface_type_str += cls.print_block(fields)

        description = cls.print_docstring(interface_type.description)
        if description:
            interface_type_str = f"{description}\n{interface_type_str}"

        return interface_type_str

    @classmethod
    def print_field(cls, name: str, field: GraphQLField, *, indent: bool = True) -> str:
        indentation: str = "  " if indent else ""

        args_str: str = ""
        if field.args:
            args: Iterable[str] = starmap(cls.print_field_argument, field.args.items())
            if not indent:
                args = (textwrap.indent(textwrap.dedent(arg), prefix="  ") for arg in args)

            args_str = "(\n" + "\n".join(args) + f"\n{indentation})"

        field_str: str = f"{indentation}{name}{args_str}: {field.type}"

        field_str += cls.print_deprecated(field.deprecation_reason)

        undine_entrypoint = get_undine_entrypoint(field)
        if undine_entrypoint is not None:
            for directive in undine_entrypoint.directives:
                field_str += cls.print_directive_usage(directive)

        undine_field = get_undine_field(field)
        if undine_field is not None:
            if undine_field.complexity != 0:
                field_str += f" @complexity(value: {undine_field.complexity})"

            for directive in undine_field.directives:
                field_str += cls.print_directive_usage(directive)

        undine_interface_field = get_undine_interface_field(field)
        if undine_interface_field is not None:
            for directive in undine_interface_field.directives:
                field_str += cls.print_directive_usage(directive)

        description = cls.print_docstring(field.description)
        if description:
            description = description.replace("\n", f"\n{indentation}").strip()
            field_str = f"{indentation}{description}\n{field_str}"

        return field_str

    @classmethod
    def print_field_argument(cls, name: str, arg: GraphQLArgument, *, indent: bool = True) -> str:
        indentation: str = "    " if indent else ""

        arg_str: str = f"{indentation}{name}: {arg.type}"

        default_ast = ast_from_value(arg.default_value, arg.type)
        if default_ast:
            arg_str += f" = {print_ast(default_ast)}"

        arg_str += cls.print_deprecated(arg.deprecation_reason)

        undine_calculation_argument = get_undine_calculation_argument(arg)
        if undine_calculation_argument is not None:
            for directive in undine_calculation_argument.directives:
                arg_str += cls.print_directive_usage(directive)

        description = cls.print_docstring(arg.description)
        if description:
            description = description.replace("\n", f"\n{indentation}").strip()
            arg_str = f"{indentation}{description}\n{arg_str}"

        return arg_str

    # --- InputObjectType ---------------------------------------------------------------------------------

    @classmethod
    def print_input_object_type(cls, input_object_type: GraphQLInputObjectType) -> str:
        input_object_type_str = f"input {input_object_type.name}"

        if is_one_of_input_object(input_object_type):
            input_object_type_str += " @oneOf"

        undine_mutation_type = get_undine_mutation_type(input_object_type)
        if undine_mutation_type is not None:
            for directive in undine_mutation_type.__directives__:
                input_object_type_str += cls.print_directive_usage(directive)

        undine_filterset = get_undine_filterset(input_object_type)
        if undine_filterset is not None:
            for directive in undine_filterset.__directives__:
                input_object_type_str += cls.print_directive_usage(directive)

        if input_object_type.fields:
            input_fields = starmap(cls.print_input_field, input_object_type.fields.items())
            input_object_type_str += cls.print_block(input_fields)

        description = cls.print_docstring(input_object_type.description)
        if description:
            input_object_type_str = f"{description}\n{input_object_type_str}"

        return input_object_type_str

    @classmethod
    def print_input_field(cls, name: str, input_field: GraphQLInputField, *, indent: bool = True) -> str:
        indentation: str = "  " if indent else ""

        input_field_str: str = f"{indentation}{name}: {input_field.type}"

        input_field_str += cls.print_deprecated(input_field.deprecation_reason)

        undine_input = get_undine_input(input_field)
        if undine_input is not None:
            for directive in undine_input.directives:
                input_field_str += cls.print_directive_usage(directive)

        undine_filter = get_undine_filter(input_field)
        if undine_filter is not None:
            for directive in undine_filter.directives:
                input_field_str += cls.print_directive_usage(directive)

        description = cls.print_docstring(input_field.description)
        if description:
            description = description.replace("\n", f"\n{indentation}").strip()
            input_field_str = f"{indentation}{description}\n{input_field_str}"

        return input_field_str

    # --- EnumType ----------------------------------------------------------------------------------------

    @classmethod
    def print_enum_type(cls, enum_type: GraphQLEnumType) -> str:
        enum_str: str = f"enum {enum_type.name}"

        undine_orderset = get_undine_orderset(enum_type)
        if undine_orderset is not None:
            for directive in undine_orderset.__directives__:
                enum_str += cls.print_directive_usage(directive)

        if enum_type.values:
            enum_values = starmap(cls.print_enum_value, enum_type.values.items())
            enum_str += cls.print_block(enum_values)

        description = cls.print_docstring(enum_type.description)
        if description:
            enum_str = f"{description}\n{enum_str}"

        return enum_str

    @classmethod
    def print_enum_value(cls, name: str, value: GraphQLEnumValue, *, indent: bool = True) -> str:
        indentation: str = "  " if indent else ""

        enum_value_str: str = f"{indentation}{name}"
        enum_value_str += cls.print_deprecated(value.deprecation_reason)

        undine_order = get_undine_order(value)
        if undine_order is not None:
            for directive in undine_order.directives:
                enum_value_str += cls.print_directive_usage(directive)

        description = cls.print_docstring(value.description)
        if description:
            description = description.replace("\n", f"\n{indentation}").strip()
            enum_value_str = f"{indentation}{description}\n{enum_value_str}"

        return enum_value_str

    # --- ScalarType --------------------------------------------------------------------------------------

    @classmethod
    def print_scalar_type(cls, scalar_type: GraphQLScalarType) -> str:
        scalar_str = f"scalar {scalar_type.name}"

        if scalar_type.specified_by_url is not None:
            scalar_str += f" @specifiedBy(url: {print_string(scalar_type.specified_by_url)})"

        undine_scalar = get_undine_scalar(scalar_type)
        if undine_scalar is not None:
            for directive in undine_scalar.directives:
                scalar_str += cls.print_directive_usage(directive)

        description = cls.print_docstring(scalar_type.description)
        if description:
            scalar_str = f"{description}\n{scalar_str}"

        return scalar_str

    # --- UnionType ---------------------------------------------------------------------------------------

    @classmethod
    def print_union_type(cls, union_type: GraphQLUnionType) -> str:
        union_str = f"union {union_type.name}"

        undine_union = get_undine_union_type(union_type)
        if undine_union is not None:
            for directive in undine_union.__directives__:
                union_str += cls.print_directive_usage(directive)

        if union_type.types:
            possible_types = " | ".join(type_.name for type_ in union_type.types)
            union_str += f" = {possible_types}"

        description = cls.print_docstring(union_type.description)
        if description:
            union_str = f"{description}\n{union_str}"

        return union_str

    # --- Directives --------------------------------------------------------------------------------------

    @classmethod
    def print_directive(cls, directive: GraphQLDirective) -> str:
        directive_str = f"directive @{directive.name}"

        if directive.args:
            args = starmap(cls.print_directive_argument, directive.args.items())
            directive_str += "(\n" + "\n".join(args) + "\n)"

        if directive.is_repeatable:
            directive_str += " repeatable"

        if directive.locations:
            directive_str += " on "
            directive_str += " | ".join(location.name for location in directive.locations)

        description = cls.print_docstring(directive.description)
        if description:
            directive_str = f"{description}\n{directive_str}"

        return directive_str

    @classmethod
    def print_directive_argument(cls, name: str, arg: GraphQLArgument, *, indent: bool = True) -> str:
        indentation: str = "  " if indent else ""

        arg_str: str = f"{indentation}{name}: {arg.type}"

        default_ast = ast_from_value(arg.default_value, arg.type)
        if default_ast:
            arg_str += f" = {print_ast(default_ast)}"

        arg_str += cls.print_deprecated(arg.deprecation_reason)

        undine_dir_arg = get_undine_directive_argument(arg)
        if undine_dir_arg is not None:
            for directive in undine_dir_arg.directives:
                arg_str += cls.print_directive_usage(directive)

        description = cls.print_docstring(arg.description)
        if description:
            description = description.replace("\n", f"\n{indentation}").strip()
            arg_str = f"{indentation}{description}\n{arg_str}"

        return arg_str

    @classmethod
    def print_directive_usage(cls, directive: Directive, *, indent: bool = True) -> str:
        indentation: str = " " if indent else ""

        output = f"{indentation}@{directive.__schema_name__}"
        if not directive.__parameters__:
            return output

        args: list[str] = []
        for parameter, value in directive.__parameters__.items():
            arg = directive.__arguments__[parameter]
            value_ast = ast_from_value(value, arg.input_type)
            if value_ast is None:
                continue

            arg_str = f"{arg.schema_name}: {print_ast(value_ast)}"
            args.append(arg_str)

        if not args:
            return output

        return f"{output}(" + ", ".join(args) + ")"

    @classmethod
    def print_deprecated(cls, reason: str | None, *, indent: bool = True) -> str:
        indentation: str = " " if indent else ""

        if reason is None:
            return ""
        if reason != DEFAULT_DEPRECATION_REASON:
            return f"{indentation}@deprecated(reason: {print_string(reason)})"
        return f"{indentation}@deprecated"

    # --- Utils --------------------------------------------------------------------------------------------

    @classmethod
    def print_docstring(cls, description: str | None) -> str:
        if description is None:
            return ""
        if is_printable_as_block_string(description):
            return print_block_string(description)
        return print_string(description)

    @classmethod
    def print_block(cls, values: Iterable[str]) -> str:
        return " {\n" + "\n".join(values) + "\n}"

    @classmethod
    def default_directive_filter(cls, directive: GraphQLDirective) -> bool:
        return not is_specified_directive(directive)

    @classmethod
    def default_type_filter(cls, named_type: GraphQLNamedType) -> bool:
        return is_defined_type(named_type)
