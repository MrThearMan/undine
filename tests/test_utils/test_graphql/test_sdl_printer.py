from __future__ import annotations

from textwrap import dedent

from django.db.models import Value
from graphql import (
    GraphQLDirective,
    GraphQLID,
    GraphQLInt,
    GraphQLNamedType,
    GraphQLNonNull,
    GraphQLSchema,
    GraphQLString,
)
from graphql.language import DirectiveLocation

from example_project.app.models import Project, Task
from undine import (
    Calculation,
    CalculationArgument,
    DjangoExpression,
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
from undine.directives import Directive, DirectiveArgument
from undine.interface import InterfaceField
from undine.scalars import ScalarType
from undine.utils.graphql.sdl_printer import SDLPrinter
from undine.utils.graphql.type_registry import GraphQLComplexityDirective, GraphQLOneOfDirective


def gql_dedent(text: str) -> str:
    return dedent(text.lstrip("\n").rstrip(" \t\n"))


def directive_filter(directive: GraphQLDirective) -> bool:
    return SDLPrinter.default_directive_filter(directive) and directive.name not in {
        GraphQLComplexityDirective.name,
        GraphQLOneOfDirective.name,
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
          name: String
          NOT: TaskFilterSet
          AND: TaskFilterSet
          OR: TaskFilterSet
          XOR: TaskFilterSet
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
    class Node(InterfaceType):
        id = InterfaceField(GraphQLNonNull(GraphQLID), resolvable_output_type=True)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        interface Node {
          id: ID!
        }

        type TaskType implements Node {
          id: ID!
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__interface_type__multiple() -> None:
    class Node(InterfaceType):
        id = InterfaceField(GraphQLNonNull(GraphQLID), resolvable_output_type=True)

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Node, Named]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        interface Named {
          name: String!
        }

        interface Node {
          id: ID!
        }

        type TaskType implements Node & Named {
          id: ID!
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
    )


def test_sdl_printer__interface_type__hierarchical() -> None:
    class Node(InterfaceType):
        id = InterfaceField(GraphQLNonNull(GraphQLID), resolvable_output_type=True)

    class Named(InterfaceType, interfaces=[Node]):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Node, Named]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_schema(query=Query)

    assert print_schema(schema) == gql_dedent(
        """
        interface Named implements Node {
          id: ID!
          name: String!
        }

        interface Node {
          id: ID!
        }

        type TaskType implements Node & Named {
          id: ID!
          name: String!
        }

        type Query {
          task(
            pk: Int!
          ): TaskType!
        }
        """
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
