from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest
from django.db.models import Value
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString, TypeMetaFieldDef, get_introspection_query

from example_project.app.models import Project, Task
from pytest_undine.client import GraphQLClientHTTPResponse
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
from undine.utils.graphql.introspection import (
    directive_introspection_type,
    field_introspection_type,
    get_directive_fields,
    get_field_fields,
    get_schema_fields,
    get_type_fields,
    resolve_type_meta_field_def,
    schema_introspection_type,
    type_introspection_type,
)


@contextmanager
def enable_visibility_patch():
    """Mirror `undine.utils.graphql.introspection.patch_introspection_schema`."""
    type_meta_field_def_resolver = TypeMetaFieldDef.resolve
    schema_fields = schema_introspection_type._fields
    directive_fields = directive_introspection_type._fields
    type_fields = type_introspection_type._fields
    field_fields = field_introspection_type._fields

    TypeMetaFieldDef.resolve = resolve_type_meta_field_def
    schema_introspection_type._fields = get_schema_fields
    directive_introspection_type._fields = get_directive_fields
    type_introspection_type._fields = get_type_fields
    field_introspection_type._fields = get_field_fields

    _re_evaluate_introspection_type_fields()

    try:
        yield
    finally:
        TypeMetaFieldDef.resolve = type_meta_field_def_resolver
        schema_introspection_type._fields = schema_fields
        directive_introspection_type._fields = directive_fields
        type_introspection_type._fields = type_fields
        field_introspection_type._fields = field_fields

        _re_evaluate_introspection_type_fields()


def _re_evaluate_introspection_type_fields():
    if "fields" in schema_introspection_type.__dict__:
        del schema_introspection_type.__dict__["fields"]

    if "fields" in directive_introspection_type.__dict__:
        del directive_introspection_type.__dict__["fields"]

    if "fields" in type_introspection_type.__dict__:
        del type_introspection_type.__dict__["fields"]

    if "fields" in field_introspection_type.__dict__:
        del field_introspection_type.__dict__["fields"]


def get_directives(response: GraphQLClientHTTPResponse) -> dict[str, dict[str, Any]]:
    schema = response.data["__schema"]
    return {directive["name"]: directive for directive in schema["directives"]}


def get_types(response: GraphQLClientHTTPResponse) -> dict[str, dict[str, Any]]:
    schema = response.data["__schema"]
    return {directive["name"]: directive for directive in schema["types"]}


def test_introspection(graphql, undine_settings):
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
        "complexity",
        "deprecated",
        "include",
        "oneOf",
        "skip",
        "specifiedBy",
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

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert len(types["Query"]["fields"]) == (1 if is_visible else 0)


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

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("TaskType" in types) is is_visible

    # 'tasks' Entrypoint is hidden, since its return type is the query type.
    assert len(types["Query"]["fields"]) == (1 if is_visible else 0)

    # 'create_task' Entrypoint is hidden, since its return type is the query type.
    assert len(types["Mutation"]["fields"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__query_type__field(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
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

    assert len(types["TaskType"]["fields"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__query_type__related(graphql, undine_settings, is_visible) -> None:
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

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("ProjectType" in types) is is_visible

    # TaskType field hidden since related QueryType is hidden
    assert len(types["TaskType"]["fields"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__query_type__connection(graphql, undine_settings, is_visible) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # 'tasks' Connection Entrypoint is hidden, since its node type is the query type.
    assert len(types["Query"]["fields"]) == (1 if is_visible else 0)

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
        name = Input()

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

    assert len(types["TaskCreateMutation"]["inputFields"]) == (1 if is_visible else 0)


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
    assert len(types["TaskCreateMutation"]["inputFields"]) == (1 if is_visible else 0)


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
    assert len(types["TaskFilterSet"]["inputFields"]) == (5 if is_visible else 4)


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
    assert len(types["TaskOrderSet"]["enumValues"]) == (2 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__interface(graphql, undine_settings, is_visible) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
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

    assert ("Named" in types) is is_visible

    # Inherited fields should be hidden
    assert len(types["TaskType"]["fields"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__interface__field(graphql, undine_settings, is_visible) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

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

    assert len(types["Named"]["fields"]) == (1 if is_visible else 0)
    assert len(types["TaskType"]["fields"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__interface__entrypoint(graphql, undine_settings, is_visible) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert len(types["Query"]["fields"]) == (1 if is_visible else 0)


@pytest.mark.parametrize("is_visible", [True, False])
def test_introspection__visibility__interface__entrypoint__connection(graphql, undine_settings, is_visible) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLString)

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return is_visible

    class Query(RootType):
        named = Entrypoint(Connection(Named))

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # Connection Entrypoint hidden since its node type is the InterfaceType.
    assert len(types["Query"]["fields"]) == (1 if is_visible else 0)


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

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    assert ("Commentable" in types) is is_visible

    # Entrypoint hidden since its type is the UnionType.
    assert len(types["Query"]["fields"]) == (1 if is_visible else 0)


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

    undine_settings.SCHEMA = create_schema(query=Query)

    query = get_introspection_query(descriptions=False)

    with enable_visibility_patch():
        response = graphql(query)

    assert response.has_errors is False, response.errors

    types = get_types(response)

    # Connection Entrypoint hidden since its node type is the UnionType.
    assert len(types["Query"]["fields"]) == (1 if is_visible else 0)


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
