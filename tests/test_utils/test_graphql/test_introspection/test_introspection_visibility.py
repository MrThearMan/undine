from __future__ import annotations

from typing import AsyncGenerator

import pytest
from django.db.models import Value
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString, get_introspection_query, version_info

from example_project.app.models import Project, Task
from tests.test_utils.test_graphql.test_introspection.helpers import enable_visibility_patch, get_directives, get_types
from undine import (
    Calculation,
    CalculationArgument,
    Directive,
    DirectiveArgument,
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
from undine.federation import ExternalDirective, FederationField, FederationType, KeyDirective, create_federation_schema
from undine.relay import Connection
from undine.typing import DjangoExpression, DjangoRequestProtocol, GQLInfo


def test_introspection__general(graphql, undine_settings):
    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    response = graphql(query)
    assert response.has_errors is False, response.errors

    directives = get_directives(response)

    assert sorted(directives) == [
        "atomic",
        "cacheRules",
        "complexity",
        *(("defer",) if version_info >= (3, 3, 0) else []),
        "deprecated",
        "include",
        "oneOf",
        "skip",
        "specifiedBy",
        *(("stream",) if version_info >= (3, 3, 0) else []),
    ]

    types = get_types(response)

    assert sorted(types) == [
        "Boolean",
        "Int",
        "Query",
        "String",
        "__Directive",
        "__DirectiveLocation",
        "__EnumValue",
        "__Field",
        "__InputValue",
        "__Schema",
        "__Type",
        "__TypeKind",
    ]


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__entrypoint(graphql, undine_settings, is_visible) -> None:
    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "foo"

        @example.visible
        def example_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

        @Entrypoint
        def filler(self) -> str:
            return "filler"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert len(types["Query"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__query_type(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

        @Entrypoint
        def filler(self) -> str:
            return "foo"

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

        @Entrypoint
        def filler(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("TaskType" in types) is is_visible

    # 'tasks' Entrypoint is hidden, since its return type is the query type.
    assert len(types["Query"]["fields"]) == (2 if is_visible else 1)

    # 'create_task' Entrypoint is hidden, since its return type is the query type.
    assert len(types["Mutation"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__query_type__field(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert len(types["TaskType"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__query_type__related(graphql, undine_settings, is_visible) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("ProjectType" in types) is is_visible

    # TaskType field hidden since related QueryType is hidden
    assert len(types["TaskType"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__query_type__connection(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

        @Entrypoint
        def filler(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # 'tasks' Connection Entrypoint is hidden, since its node type is the query type.
    assert len(types["Query"]["fields"]) == (2 if is_visible else 1)

    assert ("TaskTypeConnection" in types) is is_visible
    assert ("TaskTypeEdge" in types) is is_visible


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__query_type__connection__type_lookup(graphql, undine_settings, is_visible) -> None:
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
            edge: __type(name: "TaskTypeEdge") { name }
            connection: __type(name: "TaskTypeConnection") { name }
        }
    """

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    if is_visible:
        assert response.data["edge"]["name"] == "TaskTypeEdge"
        assert response.data["connection"]["name"] == "TaskTypeConnection"
    else:
        assert response.data["edge"] is None
        assert response.data["connection"] is None


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__calculation_argument(graphql, undine_settings, is_visible) -> None:
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

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert len(types["TaskType"]["fields"][0]["args"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__mutation_type(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("TaskCreateMutation" in types) is is_visible


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__mutation_type__input(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        filler = Input(str, hidden=True, default_value="filler")

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert len(types["TaskCreateMutation"]["inputFields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__mutation_type__related(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectInput(MutationType[Task], auto=False, kind="related"):
        name = Input()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskCreateMutation(MutationType[Task], auto=False):
        pk = Input()
        project = Input(ProjectInput)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("ProjectInput" in types) is is_visible

    # TaskCreateMutation field hidden since related MutationType is hidden
    assert len(types["TaskCreateMutation"]["inputFields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__filterset(graphql, undine_settings, is_visible) -> None:
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

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("TaskFilterSet" in types) is is_visible

    # 'filter' argument in 'tasks' Entrypoint is hidden, since it uses the TaskFilterSet
    assert len(types["Query"]["fields"][0]["args"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__filterset__filter(graphql, undine_settings, is_visible) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()
        filler = Filter("pk")

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @TaskFilterSet
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # Still contains the logical input methods
    assert len(types["TaskFilterSet"]["inputFields"]) == (6 if is_visible else 5)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__orderset(graphql, undine_settings, is_visible) -> None:
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

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("TaskOrderSet" in types) is is_visible

    # 'orderBy' argument in 'tasks' Entrypoint is hidden, since it uses the TaskOrderSet
    assert len(types["Query"]["fields"][0]["args"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__orderset__order(graphql, undine_settings, is_visible) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()
        filler = Order("pk")

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @TaskOrderSet
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # Contains both ascending and descending orders
    assert len(types["TaskOrderSet"]["enumValues"]) == (4 if is_visible else 2)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__interface(graphql, undine_settings, is_visible) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @Named
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("Named" in types) is is_visible

    # Inherited fields should be hidden
    assert len(types["TaskType"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__interface__field(graphql, undine_settings, is_visible) -> None:
    class Named(InterfaceType):
        pk = InterfaceField(GraphQLNonNull(GraphQLString))
        name = InterfaceField(GraphQLNonNull(GraphQLString))

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert len(types["Named"]["fields"]) == (2 if is_visible else 1)
    assert len(types["TaskType"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__interface__entrypoint(graphql, undine_settings, is_visible) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        @Entrypoint
        def filler(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert len(types["Query"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__interface__entrypoint__connection(graphql, undine_settings, is_visible) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        named = Entrypoint(Connection(Named))

        @Entrypoint
        def filler(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # Connection Entrypoint hidden since its node type is the InterfaceType.
    assert len(types["Query"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__union(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]):
        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

        @Entrypoint
        def filler(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("Commentable" in types) is is_visible

    # Entrypoint hidden since its type is the UnionType.
    assert len(types["Query"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__union__connection(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]):
        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        commentable = Entrypoint(Connection(Commentable))

        @Entrypoint
        def filler(self) -> str:
            return "foo"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # Connection Entrypoint hidden since its node type is the UnionType.
    assert len(types["Query"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__directive(graphql, undine_settings, is_visible) -> None:
    class Version(Directive, locations=[DirectiveLocation.OBJECT]):
        version = DirectiveArgument(GraphQLNonNull(GraphQLString))

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @Version(version="1.0.0")
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    directives = get_directives(response)

    assert ("Version" in directives) is is_visible


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__directive__argument(graphql, undine_settings, is_visible) -> None:
    class Version(Directive, locations=[DirectiveLocation.OBJECT]):
        version = DirectiveArgument(GraphQLNonNull(GraphQLString))

        @version.visible
        def version_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    @Version(version="1.0.0")
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    directives = get_directives(response)

    assert len(directives["Version"]["args"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__federation_type(graphql, undine_settings, is_visible) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("Book" in types) is is_visible


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__federation_field(graphql, undine_settings, is_visible) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

        @title.visible
        def title_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # 'isbn' is always visible; 'title' is toggled.
    assert len(types["Book"]["fields"]) == (2 if is_visible else 1)


@pytest.mark.django_db
def test_introspection__visibility__query_root__is_visible_false__hidden(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    undine_settings.SCHEMA = create_schema(query=Query)

    with enable_visibility_patch():
        response = graphql(get_introspection_query(descriptions=False))

    assert response.has_errors is False, response.errors
    assert response.data["__schema"]["queryType"] is None


@pytest.mark.django_db
def test_introspection__visibility__mutation_root__is_visible_false__hidden(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class TaskCreateMutation(MutationType[Task], auto=False):
        pk = Input()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    with enable_visibility_patch():
        response = graphql(get_introspection_query(descriptions=False))

    assert response.has_errors is False, response.errors
    assert response.data["__schema"]["mutationType"] is None


@pytest.mark.parametrize("is_visible", [True, False])
@pytest.mark.django_db
def test_introspection__visibility__subscription_entrypoint(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    async def task_stream() -> AsyncGenerator[int, None]:  # noqa: RUF029  # pragma: no cover
        yield 1

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        stream = Entrypoint(task_stream)
        filler = Entrypoint(task_stream)

        @stream.visible
        def stream_visible(self, request: DjangoRequestProtocol) -> bool:
            return is_visible

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    with enable_visibility_patch():
        response = graphql(get_introspection_query(descriptions=False))

    assert response.has_errors is False, response.errors

    subscription_type_name = response.data["__schema"]["subscriptionType"]["name"]
    types = get_types(response)
    subscription_fields = {field["name"] for field in types[subscription_type_name]["fields"]}

    if is_visible:
        assert "stream" in subscription_fields
    else:
        assert "stream" not in subscription_fields
        assert "filler" in subscription_fields


@pytest.mark.django_db
def test_introspection__visibility__subscription_root__is_visible_false__hidden(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    async def task_stream() -> AsyncGenerator[int, None]:  # noqa: RUF029  # pragma: no cover
        yield 1

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        stream = Entrypoint(task_stream)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return False

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    with enable_visibility_patch():
        response = graphql(get_introspection_query(descriptions=False))

    assert response.has_errors is False, response.errors
    assert response.data["__schema"]["subscriptionType"] is None
