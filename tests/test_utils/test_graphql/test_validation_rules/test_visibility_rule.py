from __future__ import annotations

import pytest
from django.db.models import Value
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task, TaskTypeChoices
from undine import (
    Calculation,
    CalculationArgument,
    Entrypoint,
    Field,
    Filter,
    FilterSet,
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
from undine.directives import Directive, DirectiveArgument
from undine.relay import Connection
from undine.typing import DjangoExpression, DjangoRequestProtocol, GQLInfo


@pytest.mark.parametrize("is_visible", [True, False])
def test_validation_rules__visibility_rule__entrypoint(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

        @example.visible
        def example_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            example
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'example' on type 'Query'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__query_type(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'tasks' on type 'Query'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__query_type__field(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'name' on type 'TaskType'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__query_type__related(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskType(QueryType[Task], auto=False):
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                project {
                    name
                }
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'project' on type 'TaskType'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__query_type__connection(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                edges {
                    node {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'tasks' on type 'Query'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__calculation_argument(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class Calc(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

        @value.visible
        def value_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskType(QueryType[Task], auto=False):
        custom = Field(Calc)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                custom(value: 1)
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Unknown argument 'value' on field 'TaskType.custom'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__mutation_type(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation {
            createTask(input: {name: "Test Task", type: STORY}) {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'createTask' on type 'Mutation'.",
                "extensions": {"status_code": 400},
            },
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__mutation_type__input(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation {
            createTask(input: {name: "Test Task", type: STORY}) {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Field 'name' is not defined by type 'TaskCreateMutation'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.django_db
def test_validation_rules__visibility_rule__mutation_type__input__as_variable(graphql, undine_settings):
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
    }
    # Unusual use of variables, but should still work.
    query = """
        mutation($input: TaskCreateMutation!) {
            bulkCreateTask(input: [$input]) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
            },
        ],
    }


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__mutation_type__related(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectInput(MutationType[Project], kind="related", auto=False):
        name = Input()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        project = Input(ProjectInput)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation {
            createTask(input: {name: "Test Task", type: STORY, project: {name: "Test Project"}}) {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Field 'project' is not defined by type 'TaskCreateMutation'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__mutation_type__query_type(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation {
            createTask(input: {name: "Test Task", type: STORY}) {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'createTask' on type 'Mutation'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__filterset(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @TaskFilterSet
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks(filter: {name: "foo"}) {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Unknown argument 'filter' on field 'Query.tasks'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__filterset__filter(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @TaskFilterSet
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks(filter: {name: "foo"}) {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Field 'name' is not defined by type 'TaskFilterSet'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__orderset(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @TaskOrderSet
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks(orderBy: [nameAsc]) {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Unknown argument 'orderBy' on field 'Query.tasks'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__orderset__order(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @TaskOrderSet
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks(orderBy: [nameAsc]) {
                name
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Value 'nameAsc' does not exist in 'TaskOrderSet' enum.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__interface(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class Named(InterfaceType, auto=False):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @Named
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            named {
                name
                ... on TaskType {
                    type
                }
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'named' on type 'Query'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__interface__field(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class Named(InterfaceType, auto=False):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @Named
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            named {
                name
                ... on TaskType {
                    type
                }
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'name' on type 'Named'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__interface__connection(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class Named(InterfaceType, auto=False):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @Named
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)
        named = Entrypoint(Connection(Named))

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            named {
                edges {
                    node {
                        name
                        ... on TaskType {
                            type
                        }
                    }
                }
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'named' on type 'Query'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__union(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]):
        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            commentable {
                __typename
                ... on TaskType {
                    name
                }
                ... on ProjectType {
                    name
                }
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'commentable' on type 'Query'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__union__connection(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]):
        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        commentable = Entrypoint(Connection(Commentable))

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            commentable {
                edges {
                    node {
                        __typename
                        ... on TaskType {
                            name
                        }
                        ... on ProjectType {
                            name
                        }
                    }
                }
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Cannot query field 'commentable' on type 'Query'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__directive(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class Version(Directive, locations=[DirectiveLocation.FIELD]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                name @Version(value: "1.0.0")
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Unknown directive '@Version'.",
                "extensions": {"status_code": 400},
            }
        ]


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_validation_rules__visibility_rule__directive__argument(graphql, undine_settings, is_visible) -> None:
    undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS = True

    class Version(Directive, locations=[DirectiveLocation.FIELD]):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

        @value.visible
        def value_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
            tasks {
                name @Version(value: "1.0.0")
            }
        }
    """

    response = graphql(query)

    if is_visible:
        assert response.has_errors is False, response.errors

    else:
        assert response.errors == [
            {
                "message": "Unknown argument 'value' on directive '@Version'.",
                "extensions": {"status_code": 400},
            }
        ]
