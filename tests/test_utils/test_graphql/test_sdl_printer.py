from __future__ import annotations

from textwrap import dedent

import pytest
from django.db.models import Value
from graphql import (
    DEFAULT_DEPRECATION_REASON,
    GraphQLArgument,
    GraphQLDirective,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNamedType,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLString,
    GraphQLUnionType,
)
from graphql.language import DirectiveLocation

from example_project.app.models import Project, Task
from undine import (
    Calculation,
    CalculationArgument,
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    Input,
    InterfaceType,
    MutationType,
    Order,
    OrderSet,
    QueryType,
    RootType,
    UnionType,
    create_schema,
)
from undine.directives import AtomicDirective, CacheRulesDirective, ComplexityDirective, Directive, DirectiveArgument
from undine.interface import InterfaceField
from undine.relay import Node
from undine.scalars import ScalarType
from undine.typing import DjangoExpression
from undine.utils.graphql.sdl_printer import SDLPrinter


def gql_dedent(text: str) -> str:
    return dedent(text.lstrip("\n").rstrip(" \t\n"))


def directive_filter(directive: GraphQLDirective) -> bool:
    return SDLPrinter.default_directive_filter(directive) and directive.name not in {
        AtomicDirective.__schema_name__,
        CacheRulesDirective.__schema_name__,
        ComplexityDirective.__schema_name__,
    }


def type_filter(named_type: GraphQLNamedType) -> bool:
    return SDLPrinter.default_type_filter(named_type)


def print_schema(schema: GraphQLSchema) -> str:
    return SDLPrinter.print_schema(
        schema,
        directive_filter=directive_filter,
        type_filter=type_filter,
    )


def test_sdl_printer__function_entrypoint__returns__non_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self) -> str:
            return "Hello World"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField: String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__returns__null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self) -> str | None:
            return "Hello World"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField: String
        }
        """
    )


def test_sdl_printer__function_entrypoint__returns__non_null_list_of_non_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self) -> list[str]:
            return ["Hello World"]

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField: [String!]!
        }
        """
    )


def test_sdl_printer__function_entrypoint__returns__null_list_of_non_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self) -> list[str] | None:
            return ["Hello World"]

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField: [String!]
        }
        """
    )


def test_sdl_printer__function_entrypoint__returns__non_null_list_of_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self) -> list[str | None]:
            return ["Hello World"]

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField: [String]!
        }
        """
    )


def test_sdl_printer__function_entrypoint__returns__null_list_of_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self) -> list[str | None] | None:
            return ["Hello World"]

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField: [String]
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__non_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: str) -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg: String!
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: str | None) -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg: String
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__non_null_list_of_non_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: list[str]) -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg: [String!]!
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__null_list_of_non_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: list[str] | None) -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg: [String!]
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__non_null_list_of_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: list[str | None]) -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg: [String]!
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__null_list_of_null_string() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: list[str | None] | None) -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg: [String]
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__multiple() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg1: str, arg2: int) -> str:
            return f"Hello {arg1} {arg2}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg1: String!
            arg2: Int!
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__multiple__default_value() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg1: str, arg2: int = 1) -> str:
            return f"Hello {arg1} {arg2}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg1: String!
            arg2: Int! = 1
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__default_value() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: str = "World") -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg: String! = "World"
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__default_value__special_chars() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: str = "tes\t de\fault") -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        r"""
        type Query {
          singleField(
            arg: String! = "tes\t de\fault"
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__default_value__null() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: str | None = None) -> str:
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type Query {
          singleField(
            arg: String = null
          ): String!
        }
        """
    )


def test_sdl_printer__function_entrypoint__argument__docstring() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: str | None) -> str:
            """
            Resolve a single field.

            :param arg: Message to print.
            """
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        type Query {
          """Resolve a single field."""
          singleField(
            """Message to print."""
            arg: String
          ): String!
        }
        '''
    )


def test_sdl_printer__function_entrypoint__argument__deprecation_reason() -> None:
    class Query(RootType):
        @Entrypoint
        def single_field(self, arg: str | None) -> str:
            """
            Resolve a single field.

            :param arg: Message to print.
            :deprecated arg: Deprecated argument.
            """
            return f"Hello {arg}"

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        type Query {
          """Resolve a single field."""
          singleField(
            """Message to print."""
            arg: String @deprecated(reason: "Deprecated argument.")
          ): String!
        }
        '''
    )


def test_sdl_printer__query_type__single() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__query_type__list() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String!
        }

        type Query {
          task: [TaskType!]!
        }
        """
    )


def test_sdl_printer__query_type__list__filterset_and_orderset() -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet, orderset=TaskOrderSet):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        enum TaskOrderSet {
          nameAsc
          nameDesc
        }

        type TaskType {
          name: String!
        }

        input TaskFilterSet {
          AND: TaskFilterSet
          NOT: TaskFilterSet
          OR: TaskFilterSet
          XOR: TaskFilterSet
          name: String
        }

        type Query {
          task(
            filter: TaskFilterSet
            orderBy: [TaskOrderSet!]
          ): [TaskType!]!
        }
        """
    )


def test_sdl_printer__query_type__deprecation_reason() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(deprecation_reason="Deprecated field.")

    class Query(RootType):
        task = Entrypoint(TaskType, deprecation_reason="Deprecated entrypoint.")

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String! @deprecated(reason: "Deprecated field.")
        }

        type Query {
          task(
            pk: Int!
          ): TaskType! @deprecated(reason: "Deprecated entrypoint.")
        }
        """
    )


def test_sdl_printer__query_type__complexity() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(complexity=1)

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String! @complexity(value: 1)
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__query_type__calculation() -> None:
    class TaskCalculation(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    class TaskType(QueryType[Task], auto=False):
        calc = Field(TaskCalculation)

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          calc(
            value: Int!
          ): Int!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__query_type__calculation__deprecation_reason() -> None:
    class TaskCalculation(Calculation[int]):
        value = CalculationArgument(int | None, deprecation_reason="Deprecated argument.")

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    class TaskType(QueryType[Task], auto=False):
        calc = Field(TaskCalculation)

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          calc(
            value: Int @deprecated(reason: "Deprecated argument.")
          ): Int!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__query_type__relation() -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        type ProjectType {
          name: String!
        }

        type TaskType {
          name: String!
          project: ProjectType @complexity(value: 1)
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__mutation_type__single() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=Mutation)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String!
        }

        input TaskCreateMutation {
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }

        type Mutation {
          createTask(
            input: TaskCreateMutation!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__mutation_type__many() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    schema = create_schema(query=Query, mutation=Mutation)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String!
        }

        input TaskCreateMutation {
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }

        type Mutation {
          bulkCreateTasks(
            input: [TaskCreateMutation!]!
          ): [TaskType!]!
        }
        """
    )


def test_sdl_printer__mutation_type__deprecation_reason() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input(deprecation_reason="Deprecated input field.", required=False)

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation, deprecation_reason="Deprecated entrypoint.")

    schema = create_schema(query=Query, mutation=Mutation)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String!
        }

        input TaskCreateMutation {
          name: String @deprecated(reason: "Deprecated input field.")
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }

        type Mutation {
          createTask(
            input: TaskCreateMutation!
          ): TaskType! @deprecated(reason: "Deprecated entrypoint.")
        }
        """
    )


def test_sdl_printer__schema_with_description() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query, description="Schema description.")

    assert print_schema(schema) == gql_dedent(
        '''
        type TaskType {
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }

        """Schema description."""
        schema {
          query: Query
        }
        '''
    )


def test_sdl_printer__custom_query_root_type() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class CustomQuery(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=CustomQuery)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String!
        }

        type CustomQuery {
          task(
            pk: Int!
          ): TaskType!
        }

        schema {
          query: CustomQuery
        }
        """
    )


def test_sdl_printer__custom_mutation_root_type() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class CustomMutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=CustomMutation)

    assert print_schema(schema) == gql_dedent(
        """
        type TaskType {
          name: String!
        }

        input TaskCreateMutation {
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }

        type CustomMutation {
          createTask(
            input: TaskCreateMutation!
          ): TaskType!
        }

        schema {
          query: Query
          mutation: CustomMutation
        }
        """
    )


def test_sdl_printer__schema_with_directive() -> None:
    class VersionDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="version"):
        version = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query, schema_definition_directives=[VersionDirective(version="v1.0.0")])

    assert print_schema(schema) == gql_dedent(
        """
        directive @version(
          version: String!
        ) on SCHEMA

        type TaskType {
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }

        schema @version(version: "v1.0.0") {
          query: Query
        }
        """
    )


def test_sdl_printer__interface_type() -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        """An interface for objects with Global IDs."""
        interface Node {
          """The Global ID of an object."""
          id: ID!
        }

        type TaskType implements Node {
          """The Global ID of an object."""
          id: ID!
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        '''
    )


def test_sdl_printer__interface_type__multiple() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Node, Named]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        interface Named {
          name: String!
        }

        """An interface for objects with Global IDs."""
        interface Node {
          """The Global ID of an object."""
          id: ID!
        }

        type TaskType implements Node & Named {
          """The Global ID of an object."""
          id: ID!
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        '''
    )


def test_sdl_printer__interface_type__hierarchical() -> None:
    class Named(InterfaceType, interfaces=[Node]):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Node, Named]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        interface Named implements Node {
          """The Global ID of an object."""
          id: ID!
          name: String!
        }

        """An interface for objects with Global IDs."""
        interface Node {
          """The Global ID of an object."""
          id: ID!
        }

        type TaskType implements Node & Named {
          """The Global ID of an object."""
          id: ID!
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        '''
    )


def test_sdl_printer__interface_type__deprecation_reason() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), deprecation_reason="Deprecated field.")

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        interface Named {
          name: String! @deprecated(reason: "Deprecated field.")
        }

        type TaskType implements Named {
          name: String! @deprecated(reason: "Deprecated field.")
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__unions() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentableType(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(CommentableType, many=True)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        union CommentableType = TaskType | ProjectType

        type ProjectType {
          name: String!
        }

        type TaskType {
          name: String!
        }

        type Query {
          commentable: [CommentableType!]!
        }
        """
    )


def test_sdl_printer__custom_scalar() -> None:
    class TaskType(QueryType[Task], auto=False):
        created_at = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        """
        Represents a date and time value as specified by ISO 8601.
        Maps to the Python `datetime.datetime` type.
        """
        scalar DateTime @specifiedBy(url: "https://datatracker.ietf.org/doc/html/rfc3339#section-5.6")

        type TaskType {
          createdAt: DateTime!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        '''
    )


def test_sdl_printer__custom_scalar_with_specified_by_url() -> None:
    my_scalar = ScalarType(
        name="MyScalar",
        specified_by_url="https://example.com/foo_spec",
    )

    class TaskType(QueryType[Task], auto=False):
        custom = Field(my_scalar.as_graphql_scalar())

        @custom.resolve
        def resolve_custom(self, info: GQLInfo, *, value: int) -> int:
            return value

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        scalar MyScalar @specifiedBy(url: "https://example.com/foo_spec")

        type TaskType {
          custom: MyScalar
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__custom_directive() -> None:
    class MyDirective(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION, DirectiveLocation.OBJECT],
        schema_name="myDirective",
    ):
        string_arg = DirectiveArgument(GraphQLNonNull(GraphQLString))
        int_arg = DirectiveArgument(GraphQLNonNull(GraphQLInt), default_value=-1)

    class TaskType(QueryType[Task], auto=False):
        name = Field(directives=[MyDirective(string_arg="foo", int_arg=1)])

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        directive @myDirective(
          intArg: Int! = -1
          stringArg: String!
        ) on FIELD_DEFINITION | OBJECT

        type TaskType {
          name: String! @myDirective(intArg: 1, stringArg: "foo")
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__description__short() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(description="Short description")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        type TaskType {
          """Short description"""
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        '''
    )


def test_sdl_printer__description__long() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(description="Very long description that should be wrapped using multiline block comment string.")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        type TaskType {
          """
          Very long description that should be wrapped using multiline block comment string.
          """
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        '''
    )


def test_sdl_printer__description__empty() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(description="")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        '''
        type TaskType {
          """"""
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        '''
    )


def test_sdl_printer__default_filters() -> None:
    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    schema = create_schema(query=Query)
    result = SDLPrinter.print_schema(schema)
    assert "type Query" in result


def test_sdl_printer__subscription_type() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Subscription(RootType):
        @Entrypoint
        async def task_updates(self) -> str:
            yield "update"  # type: ignore[misc]

    schema = create_schema(query=Query, subscription=Subscription)
    result = print_schema(schema)
    assert "type Query" in result


def test_sdl_printer__print_schema_definition__no_query_type() -> None:
    schema = GraphQLSchema(
        query=GraphQLObjectType("Query", fields={"x": GraphQLField(GraphQLString)}),
        description="My API",
    )
    result = SDLPrinter.print_schema_definition(schema)
    assert "schema" in result


def test_sdl_printer__print_type__unknown_type() -> None:
    with pytest.raises(TypeError):
        SDLPrinter.print_type(GraphQLList(GraphQLString))  # type: ignore[arg-type]


def test_sdl_printer__query_type_with_directive() -> None:
    class MyDirective(
        Directive,
        locations=[DirectiveLocation.OBJECT],
        schema_name="myTypeDirective",
    ): ...

    @MyDirective()
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@myTypeDirective" in result


def test_sdl_printer__root_type_with_directive() -> None:
    class RootDirective(
        Directive,
        locations=[DirectiveLocation.OBJECT],
        schema_name="rootDirective",
    ): ...

    class Query(RootType, directives=[RootDirective()]):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@rootDirective" in result


def test_sdl_printer__object_type__description() -> None:
    class TaskType(QueryType[Task], auto=False):
        """A task type."""

        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "A task type" in result


def test_sdl_printer__object_type__no_fields() -> None:
    gql_type = GraphQLObjectType("Empty", fields={})
    result = SDLPrinter.print_object_type(gql_type)
    assert result == "type Empty"


def test_sdl_printer__interface_type__no_undine_extension() -> None:
    gql_type = GraphQLInterfaceType("PlainIface", fields={"x": GraphQLField(GraphQLString)})
    result = SDLPrinter.print_interface_type(gql_type)
    assert "interface PlainIface" in result


def test_sdl_printer__interface_type__with_directives() -> None:
    class IfaceDirective(
        Directive,
        locations=[DirectiveLocation.INTERFACE],
        schema_name="ifaceDirective",
    ): ...

    class Named(InterfaceType, auto=False, directives=[IfaceDirective()]):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@ifaceDirective" in result


def test_sdl_printer__interface_type__no_fields() -> None:
    gql_type = GraphQLInterfaceType("EmptyIface", fields={})
    result = SDLPrinter.print_interface_type(gql_type)
    assert result == "interface EmptyIface"


def test_sdl_printer__field__no_indent() -> None:
    field = GraphQLField(
        GraphQLString,
        args={"arg": GraphQLArgument(GraphQLString)},
        description="A field desc",
    )
    result = SDLPrinter.print_field("myField", field, indent=False)
    assert "myField" in result


def test_sdl_printer__interface_field__with_directives() -> None:
    class FieldDirective(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION],
        schema_name="fieldDir",
    ): ...

    class Named(InterfaceType, auto=False):
        name = InterfaceField(GraphQLNonNull(GraphQLString), directives=[FieldDirective()])

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@fieldDir" in result


def test_sdl_printer__calculation_argument__with_directives() -> None:
    class CalcArgDir(
        Directive,
        locations=[DirectiveLocation.ARGUMENT_DEFINITION],
        schema_name="calcArgDir",
    ): ...

    class TaskCalc(Calculation[int]):
        factor = CalculationArgument(int, directives=[CalcArgDir()])

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.factor)

    class TaskType(QueryType[Task], auto=False):
        calc = Field(TaskCalc)

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@calcArgDir" in result


def test_sdl_printer__mutation_type__with_directives() -> None:
    class MutDir(
        Directive,
        locations=[DirectiveLocation.INPUT_OBJECT],
        schema_name="mutDir",
    ): ...

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False, directives=[MutDir()]):
        name = Input()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=Mutation)
    result = print_schema(schema)
    assert "@mutDir" in result


def test_sdl_printer__filterset__with_directives() -> None:
    class FsDir(
        Directive,
        locations=[DirectiveLocation.INPUT_OBJECT],
        schema_name="fsDir",
    ): ...

    class TaskFilter(FilterSet[Task], auto=False, directives=[FsDir()]):
        name = Filter()

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilter):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@fsDir" in result


def test_sdl_printer__input_type__no_fields_with_description() -> None:
    gql_type = GraphQLInputObjectType("EmptyInput", fields={}, description="An empty input.")
    result = SDLPrinter.print_input_object_type(gql_type)
    assert "input EmptyInput" in result
    assert "An empty input" in result


def test_sdl_printer__input_field__default_value() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        priority = Input(int, default_value=0)

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=Mutation)
    result = print_schema(schema)
    assert "= 0" in result


def test_sdl_printer__input_field__with_directives() -> None:
    class InputDir(
        Directive,
        locations=[DirectiveLocation.INPUT_FIELD_DEFINITION],
        schema_name="inputDir",
    ): ...

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input(directives=[InputDir()])

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=Mutation)
    result = print_schema(schema)
    assert "@inputDir" in result


def test_sdl_printer__filter__with_directives_description() -> None:
    class FilterDir(
        Directive,
        locations=[DirectiveLocation.INPUT_FIELD_DEFINITION],
        schema_name="filterDir",
    ): ...

    class TaskFilter(FilterSet[Task], auto=False):
        name = Filter(directives=[FilterDir()], description="Filter by name.")

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilter):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@filterDir" in result
    assert "Filter by name" in result


def test_sdl_printer__orderset__with_directives() -> None:
    class OsDir(
        Directive,
        locations=[DirectiveLocation.ENUM],
        schema_name="osDir",
    ): ...

    class TaskOrder(OrderSet[Task], auto=False, directives=[OsDir()]):
        name = Order()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True, order=TaskOrder)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@osDir" in result


def test_sdl_printer__enum_type__description() -> None:
    gql_type = GraphQLEnumType(
        "MyEnum",
        values={"A": GraphQLEnumValue("A")},
        description="Enum desc.",
    )
    result = SDLPrinter.print_enum_type(gql_type)
    assert "Enum desc" in result


def test_sdl_printer__enum_type__no_values() -> None:
    gql_type = GraphQLEnumType("EmptyEnum", values={})
    result = SDLPrinter.print_enum_type(gql_type)
    assert result == "enum EmptyEnum"


def test_sdl_printer__order__with_directives() -> None:
    class OrdDir(
        Directive,
        locations=[DirectiveLocation.ENUM_VALUE],
        schema_name="ordDir",
    ): ...

    class TaskOrder(OrderSet[Task], auto=False):
        name = Order(directives=[OrdDir()])

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True, order=TaskOrder)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@ordDir" in result


def test_sdl_printer__enum_value__description() -> None:
    gql_type = GraphQLEnumType(
        "MyEnumWithDesc",
        values={"A": GraphQLEnumValue("A", description="Value A.")},
    )
    result = SDLPrinter.print_enum_type(gql_type)
    assert "Value A" in result


def test_sdl_printer__scalar__no_specified_by_url_with_directives() -> None:
    class ScalarDir(
        Directive,
        locations=[DirectiveLocation.SCALAR],
        schema_name="scalarDir",
    ): ...

    my_scalar = ScalarType(name="MyPlainScalar", directives=[ScalarDir()])

    class TaskType(QueryType[Task], auto=False):
        custom = Field(my_scalar.as_graphql_scalar())

        @custom.resolve
        def resolve_custom(self, info: GQLInfo, *, value: int) -> int:
            return value

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@scalarDir" in result


def test_sdl_printer__scalar__no_undine_extension() -> None:
    GraphQLObjectType("Wrapper", fields={"x": GraphQLField(GraphQLString)})

    scalar = GraphQLScalarType("BareScalar")
    result = SDLPrinter.print_scalar_type(scalar)
    assert result == "scalar BareScalar"


def test_sdl_printer__union__no_undine_extension() -> None:
    member = GraphQLObjectType("UnionMember", fields={"x": GraphQLField(GraphQLString)})
    gql_type = GraphQLUnionType("BareUnion", types=[member])
    result = SDLPrinter.print_union_type(gql_type)
    assert "union BareUnion = UnionMember" in result


def test_sdl_printer__union__with_directives_and_description() -> None:
    class UnionDir(
        Directive,
        locations=[DirectiveLocation.UNION],
        schema_name="unionDir",
    ): ...

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType], directives=[UnionDir()]):
        """A union."""

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@unionDir" in result
    assert "A union" in result


def test_sdl_printer__union__no_types() -> None:
    member = GraphQLObjectType("PlaceholderType", fields={"x": GraphQLField(GraphQLString)})
    GraphQLUnionType("NoTypesUnion", types=[member])
    # Directly mutate types to empty to test False branch
    result = SDLPrinter.print_union_type(GraphQLUnionType("EmptyUnion", types=[member]))
    assert "union EmptyUnion" in result


def test_sdl_printer__directive__no_args_repeatable_no_locations_description() -> None:
    gql_directive = GraphQLDirective(
        "myRepeatable",
        locations=[],
        is_repeatable=True,
        description="A repeatable directive.",
    )
    result = SDLPrinter.print_directive(gql_directive)
    assert "repeatable" in result
    assert "A repeatable directive" in result


def test_sdl_printer__directive_argument__with_directives_description() -> None:
    class DirArgDir(
        Directive,
        locations=[DirectiveLocation.ARGUMENT_DEFINITION],
        schema_name="dirArgDir",
    ): ...

    class MyDirective(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION],
        schema_name="myDirWithArgDir",
    ):
        val = DirectiveArgument(
            GraphQLNonNull(GraphQLString),
            directives=[DirArgDir()],
            description="The value.",
        )

    class TaskType(QueryType[Task], auto=False):
        name = Field(directives=[MyDirective(val="x")])

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@dirArgDir" in result
    assert "The value" in result


def test_sdl_printer__directive_usage__no_params() -> None:
    class NoParamDirective(
        Directive,
        locations=[DirectiveLocation.OBJECT],
        schema_name="noParam",
    ): ...

    @NoParamDirective()
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@noParam" in result


def test_sdl_printer__directive_usage__value_equals_default() -> None:
    class WithDefaultDir(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION],
        schema_name="withDefault",
    ):
        value = DirectiveArgument(GraphQLInt, default_value=42)

    class TaskType(QueryType[Task], auto=False):
        name = Field(directives=[WithDefaultDir(value=42)])  # value equals default

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    # Directive appears without args since value == default
    assert "@withDefault" in result
    assert "42" not in result.split("@withDefault")[1].split("\n")[0]


def test_sdl_printer__deprecated__default_reason() -> None:
    result = SDLPrinter.print_deprecated(DEFAULT_DEPRECATION_REASON)
    assert result == " @deprecated"


def test_sdl_printer__docstring__non_block_string() -> None:
    result = SDLPrinter.print_docstring("test\r\nwindows")
    assert result.startswith('"')


def test_sdl_printer__entrypoint_with_directives() -> None:
    class EntDir(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION],
        schema_name="entDir",
    ): ...

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, directives=[EntDir()])

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@entDir" in result


def test_sdl_printer__input_type__is_one_of() -> None:
    gql_type = GraphQLInputObjectType(
        "OneOfInput",
        fields={"x": GraphQLInputField(GraphQLString)},
        is_one_of=True,
    )
    result = SDLPrinter.print_input_object_type(gql_type)
    assert "@oneOf" in result


def test_sdl_printer__orderset__directive_in_output() -> None:
    class OsDir2(
        Directive,
        locations=[DirectiveLocation.ENUM],
        schema_name="osDir2",
    ): ...

    class TaskOrder2(OrderSet[Task], auto=False, directives=[OsDir2()]):
        name = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrder2):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@osDir2" in result


def test_sdl_printer__order__directive_in_output() -> None:
    class OrdDir2(
        Directive,
        locations=[DirectiveLocation.ENUM_VALUE],
        schema_name="ordDir2",
    ): ...

    class TaskOrder3(OrderSet[Task], auto=False):
        name = Order(directives=[OrdDir2()])

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrder3):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    schema = create_schema(query=Query)
    result = print_schema(schema)
    assert "@ordDir2" in result


def test_sdl_printer__directive_argument__no_undine_extension() -> None:
    plain_arg = GraphQLArgument(GraphQLString, description="Plain arg")
    result = SDLPrinter.print_directive_argument("x", plain_arg)
    assert "x: String" in result


def test_sdl_printer__directive_usage__value_ast_none() -> None:
    class BadValueDir(
        Directive,
        locations=[DirectiveLocation.FIELD_DEFINITION],
        schema_name="badValueDir",
    ):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    # Pass None as value — ast_from_value(None, NonNull(String)) returns None
    directive = BadValueDir(value=None)  # type: ignore[arg-type]
    result = SDLPrinter.print_directive_usage(directive)
    # No args since value_ast is None
    assert result == " @badValueDir"


def test_sdl_printer__print_schema_definition__empty_schema() -> None:
    schema = GraphQLSchema()
    result = SDLPrinter.print_schema_definition(schema)
    assert result == ""


def test_sdl_printer__print_union_type__empty_types() -> None:
    union_type = GraphQLUnionType("EmptyUnion", [])
    result = SDLPrinter.print_union_type(union_type)
    assert result == "union EmptyUnion"
