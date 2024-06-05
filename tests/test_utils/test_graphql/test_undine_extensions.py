from __future__ import annotations

from django.db.models import Value
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

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
    InterfaceField,
    InterfaceType,
    MutationType,
    Order,
    OrderSet,
    QueryType,
    RootType,
    UnionType,
    create_schema,
)
from undine.converters import convert_to_graphql_type
from undine.directives import Directive, DirectiveArgument
from undine.relay import Connection
from undine.scalars import ScalarType
from undine.utils.graphql.undine_extensions import (
    get_undine_calculation_argument,
    get_undine_connection,
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
    get_undine_root_type,
    get_undine_scalar,
    get_undine_schema_directives,
    get_undine_union_type,
)


def test_undine_extensions__get_undine_schema_directives() -> None:
    class VersionDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="version"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class Query(RootType):
        @Entrypoint
        def foo(self) -> str:
            return "bar"

    directives: list[Directive] = [VersionDirective(value="v1.0.0")]

    schema = create_schema(query=Query, schema_definition_directives=directives)

    assert get_undine_schema_directives(schema) == directives


def test_undine_extensions__get_undine_schema_directives__not_found() -> None:
    class Query(RootType):
        @Entrypoint
        def foo(self) -> str:
            return "bar"

    schema = create_schema(query=Query)

    assert get_undine_schema_directives(schema) is None


def test_undine_extensions__get_undine_root_type() -> None:
    class Query(RootType):
        @Entrypoint
        def foo(self) -> str:
            return "bar"

    object_type = Query.__output_type__()

    assert get_undine_root_type(object_type) == Query


def test_undine_extensions__get_undine_entrypoint() -> None:
    class Query(RootType):
        @Entrypoint
        def foo(self) -> str:
            return "bar"

    field = Query.foo.as_graphql_field()

    assert get_undine_entrypoint(field) == Query.foo


def test_undine_extensions__get_undine_query_type() -> None:
    class TaskType(QueryType[Task]): ...

    object_type = TaskType.__output_type__()

    assert get_undine_query_type(object_type) == TaskType


def test_undine_extensions__get_undine_field() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    field = TaskType.name.as_graphql_field()

    assert get_undine_field(field) == TaskType.name


def test_undine_extensions__get_undine_interface_type() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    interface = Named.__interface__()

    assert get_undine_interface_type(interface) == Named


def test_undine_extensions__get_undine_interface_field() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    field = Named.name.as_graphql_field()

    assert get_undine_interface_field(field) == Named.name


def test_undine_extensions__get_undine_mutation_type() -> None:
    class TaskCreateMutation(MutationType[Task]):
        name = Input()

    input_object = TaskCreateMutation.__input_type__()

    assert get_undine_mutation_type(input_object) == TaskCreateMutation


def test_undine_extensions__get_undine_input() -> None:
    class TaskCreateMutation(MutationType[Task]):
        name = Input()

    input_field = TaskCreateMutation.name.as_graphql_input_field()

    assert get_undine_input(input_field) == TaskCreateMutation.name


def test_undine_extensions__get_undine_filterset() -> None:
    class TaskFilterSet(FilterSet[Task]):
        name = Filter()

    input_object = TaskFilterSet.__input_type__()

    assert get_undine_filterset(input_object) == TaskFilterSet


def test_undine_extensions__get_undine_filter() -> None:
    class TaskFilterSet(FilterSet[Task]):
        name = Filter()

    input_field = TaskFilterSet.name.as_graphql_input_field()

    assert get_undine_filter(input_field) == TaskFilterSet.name


def test_undine_extensions__get_undine_orderset() -> None:
    class TaskOrderSet(OrderSet[Task]):
        name = Order()

    enum_type = TaskOrderSet.__enum_type__()

    assert get_undine_orderset(enum_type) == TaskOrderSet


def test_undine_extensions__get_undine_order() -> None:
    class TaskOrderSet(OrderSet[Task]):
        name = Order()

    enum_value = TaskOrderSet.name.as_graphql_enum_value()

    assert get_undine_order(enum_value) == TaskOrderSet.name


def test_undine_extensions__get_undine_connection() -> None:
    class TaskType(QueryType[Task]): ...

    connection = Connection(TaskType)

    object_type = convert_to_graphql_type(connection)

    assert get_undine_connection(object_type) == connection


def test_undine_extensions__get_undine_directive() -> None:
    class VersionDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="version"):
        version = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directive = VersionDirective.__directive__()

    assert get_undine_directive(directive) == VersionDirective


def test_undine_extensions__get_undine_directive_argument() -> None:
    class VersionDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="version"):
        version = DirectiveArgument(GraphQLNonNull(GraphQLString))

    arg = VersionDirective.version.as_graphql_argument()

    assert get_undine_directive_argument(arg) == VersionDirective.version


def test_undine_extensions__get_undine_scalar() -> None:
    scalar: ScalarType[str, str] = ScalarType(name="MyScalar")

    scalar_type = scalar.as_graphql_scalar()

    assert get_undine_scalar(scalar_type) == scalar


def test_undine_extensions__get_undine_union_type() -> None:
    class TaskType(QueryType[Task]): ...
    class ProjectType(QueryType[Project]): ...

    class MyUnion(UnionType[TaskType, ProjectType]): ...

    union_type = MyUnion.__union_type__()

    assert get_undine_union_type(union_type) == MyUnion


def test_undine_extensions__get_undine_calculation_argument() -> None:
    class TaskCalculation(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    arg = TaskCalculation.value.as_graphql_argument()

    assert get_undine_calculation_argument(arg) == TaskCalculation.value
