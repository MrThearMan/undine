from __future__ import annotations

from typing import TypedDict

from django.db import models
from django.db.models.functions.datetime import Now
from graphql import (
    GraphQLArgument,
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLString,
    Undefined,
)

from example_project.app.models import Comment, Project, Task
from undine import Input, MutationType, QueryType
from undine.converters import convert_to_graphql_argument_map
from undine.utils.lazy import LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.utils.reflection import get_signature


def test_to_argument_map__function__type():
    def func(arg: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result == {"arg": GraphQLArgument(GraphQLNonNull(GraphQLString))}


def test_to_argument_map__function__type__nullable():
    def func(arg: str | None) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert sorted(result) == ["arg"]
    assert isinstance(result["arg"], GraphQLArgument)
    assert result["arg"].type == GraphQLString


def test_to_argument_map__function__default_value():
    def func(arg: str = "foo") -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].default_value == "foo"


def test_to_argument_map__function__default_value__none():
    def func(arg: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].default_value is Undefined


def test_to_argument_map__function__description():
    def func(arg: str) -> int:
        """
        Description.

        :param arg: Argument description.
        """

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].description == "Argument description."


def test_to_argument_map__function__description__none():
    def func(arg: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].description is None


def test_to_argument_map__function__deprecation_reason():
    def func(arg: str) -> int:
        """
        Description.

        :deprecated arg: Use something else.
        """

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].deprecation_reason == "Use something else."


def test_to_argument_map__function__deprecation_reason__none():
    def func(arg: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].deprecation_reason is None


def test_to_argument_map__function__schema_name():
    def func(new_argument: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert sorted(result) == ["newArgument"]


def test_to_argument_map__function__typed_dict():
    class UserParams(TypedDict):
        name: str
        age: int | None

    def func(arg: UserParams) -> int: ...

    get_signature(func)  # Cache signature since we use a custom type hint (UserParams)

    result = convert_to_graphql_argument_map(func, many=False)

    assert sorted(result) == ["arg"]
    assert isinstance(result["arg"], GraphQLArgument)
    assert isinstance(result["arg"].type, GraphQLNonNull)
    assert isinstance(result["arg"].type.of_type, GraphQLInputObjectType)

    assert result["arg"].type.of_type.name == "UserParams"

    assert sorted(result["arg"].type.of_type.fields) == ["age", "name"]

    assert result["arg"].type.of_type.fields["age"].type == GraphQLInt
    assert result["arg"].type.of_type.fields["name"].type == GraphQLNonNull(GraphQLString)


def test_to_argument_map__model_field():
    field = Task._meta.get_field("name")
    assert convert_to_graphql_argument_map(field, many=False) == {}


def test_to_argument_map__expression():
    assert convert_to_graphql_argument_map(Now(), many=False) == {}


def test_to_argument_map__subquery():
    sq = models.Subquery(Task.objects.values("id"))
    assert convert_to_graphql_argument_map(sq, many=False) == {}


def test_to_argument_map__lazy_query_type__single():
    class ProjectType(QueryType, model=Project, filterset=True, orderset=True): ...

    lazy = LazyQueryType(field=Task._meta.get_field("project"))

    assert convert_to_graphql_argument_map(lazy, many=False) == {}


def test_to_argument_map__lazy_query_type__many():
    class ProjectType(QueryType, model=Project, filterset=True, orderset=True): ...

    lazy = LazyQueryType(field=Task._meta.get_field("project"))

    result = convert_to_graphql_argument_map(lazy, many=True)
    assert sorted(result) == ["filter", "orderBy"]

    assert isinstance(result["filter"], GraphQLArgument)
    assert isinstance(result["filter"].type, GraphQLInputObjectType)

    assert result["filter"].type.name == "ProjectFilterSet"

    assert isinstance(result["orderBy"], GraphQLArgument)
    assert isinstance(result["orderBy"].type, GraphQLList)
    assert isinstance(result["orderBy"].type.of_type, GraphQLNonNull)
    assert isinstance(result["orderBy"].type.of_type.of_type, GraphQLEnumType)

    assert result["orderBy"].type.of_type.of_type.name == "ProjectOrderSet"


def test_to_argument_map__LazyLambdaQueryType():
    class ProjectType(QueryType, model=Project, filterset=True, orderset=True): ...

    lazy = LazyLambdaQueryType(callback=lambda: ProjectType)

    result = convert_to_graphql_argument_map(lazy, many=True)
    assert sorted(result) == ["filter", "orderBy"]


def test_to_argument_map__lazy_query_type_union():
    field = Comment._meta.get_field("target")
    lazy = LazyQueryTypeUnion(field)
    assert convert_to_graphql_argument_map(lazy, many=False) == {}


def test_to_argument_map__query_type():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True): ...

    assert convert_to_graphql_argument_map(TaskType, many=False) == {}


def test_to_argument_map__query_type__entrypoint():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True): ...

    results = convert_to_graphql_argument_map(TaskType, many=False, entrypoint=True)

    assert sorted(results) == ["pk"]
    assert isinstance(results["pk"], GraphQLArgument)
    assert results["pk"].type == GraphQLNonNull(GraphQLInt)


def test_to_argument_map__query_type__many():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True): ...

    result = convert_to_graphql_argument_map(TaskType, many=True)
    assert sorted(result) == ["filter", "orderBy"]

    assert isinstance(result["filter"], GraphQLArgument)
    assert isinstance(result["filter"].type, GraphQLInputObjectType)

    assert result["filter"].type.name == "TaskFilterSet"

    assert isinstance(result["orderBy"], GraphQLArgument)
    assert isinstance(result["orderBy"].type, GraphQLList)
    assert isinstance(result["orderBy"].type.of_type, GraphQLNonNull)
    assert isinstance(result["orderBy"].type.of_type.of_type, GraphQLEnumType)

    assert result["orderBy"].type.of_type.of_type.name == "TaskOrderSet"


def test_to_argument_map__query_type__many__entrypoint():
    class TaskType(QueryType, model=Task, filterset=True, orderset=True): ...

    result = convert_to_graphql_argument_map(TaskType, many=True, entrypoint=True)
    assert sorted(result) == ["filter", "orderBy"]

    assert isinstance(result["filter"], GraphQLArgument)
    assert isinstance(result["filter"].type, GraphQLInputObjectType)

    assert result["filter"].type.name == "TaskFilterSet"

    assert isinstance(result["orderBy"], GraphQLArgument)
    assert isinstance(result["orderBy"].type, GraphQLList)
    assert isinstance(result["orderBy"].type.of_type, GraphQLNonNull)
    assert isinstance(result["orderBy"].type.of_type.of_type, GraphQLEnumType)

    assert result["orderBy"].type.of_type.of_type.name == "TaskOrderSet"


def test_to_argument_map__query_type__many__no_filterset_or_orderset():
    class TaskType(QueryType, model=Task): ...

    assert convert_to_graphql_argument_map(TaskType, many=True) == {}


def test_to_argument_map__mutation_type__create_mutation():
    class TaskCreateMutation(MutationType, model=Task):
        name = Input()

    result = convert_to_graphql_argument_map(TaskCreateMutation, many=False)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.name == "TaskCreateMutation"

    assert result["input"].type.of_type.fields["name"].type == GraphQLNonNull(GraphQLString)


def test_to_argument_map__mutation_type__create_mutation__entrypoint():
    class TaskCreateMutation(MutationType, model=Task):
        name = Input()

    result = convert_to_graphql_argument_map(TaskCreateMutation, many=False, entrypoint=True)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.name == "TaskCreateMutation"

    assert result["input"].type.of_type.fields["name"].type == GraphQLNonNull(GraphQLString)


def test_to_argument_map__mutation_type__update_mutation():
    class TaskUpdateMutation(MutationType, model=Task):
        name = Input()

    result = convert_to_graphql_argument_map(TaskUpdateMutation, many=False)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.name == "TaskUpdateMutation"

    assert result["input"].type.of_type.fields["name"].type == GraphQLString


def test_to_argument_map__mutation_type__update_mutation__entrypoint():
    class TaskUpdateMutation(MutationType, model=Task):
        name = Input()

    result = convert_to_graphql_argument_map(TaskUpdateMutation, many=False, entrypoint=True)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.name == "TaskUpdateMutation"

    assert result["input"].type.of_type.fields["name"].type == GraphQLString


def test_to_argument_map__mutation_type__delete_mutation():
    class TaskDeleteMutation(MutationType, model=Task): ...

    result = convert_to_graphql_argument_map(TaskDeleteMutation, many=False)

    assert result == {"input": GraphQLArgument(GraphQLNonNull(GraphQLInt))}


def test_to_argument_map__mutation_type__custom_mutation():
    class TaskMutation(MutationType, model=Task): ...

    result = convert_to_graphql_argument_map(TaskMutation, many=False)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)


def test_to_argument_map__mutation_type__bulk_create_mutation():
    class TaskBulkCreateMutation(MutationType, model=Task):
        name = Input()

    result = convert_to_graphql_argument_map(TaskBulkCreateMutation, many=True)

    assert sorted(result) == [
        "batchSize",
        "ignoreConflicts",
        "input",
        "uniqueFields",
        "updateConflicts",
        "updateFields",
    ]

    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLList)
    assert isinstance(result["input"].type.of_type.of_type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type.of_type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.of_type.of_type.name == "TaskBulkCreateMutation"

    assert isinstance(result["batchSize"], GraphQLArgument)
    assert result["batchSize"].type == GraphQLInt
    assert result["batchSize"].default_value is None
    assert result["batchSize"].description is not None
    assert result["batchSize"].out_name == "batch_size"

    assert isinstance(result["ignoreConflicts"], GraphQLArgument)
    assert result["ignoreConflicts"].type == GraphQLBoolean
    assert result["ignoreConflicts"].default_value is False
    assert result["ignoreConflicts"].description is not None
    assert result["ignoreConflicts"].out_name == "ignore_conflicts"

    assert isinstance(result["updateConflicts"], GraphQLArgument)
    assert result["updateConflicts"].type == GraphQLBoolean
    assert result["updateConflicts"].default_value is False
    assert result["updateConflicts"].description is not None
    assert result["updateConflicts"].out_name == "update_conflicts"

    assert isinstance(result["updateFields"], GraphQLArgument)
    assert result["updateFields"].default_value is None
    assert result["updateFields"].description is not None
    assert result["updateFields"].out_name == "update_fields"

    assert isinstance(result["updateFields"].type, GraphQLList)
    assert isinstance(result["updateFields"].type.of_type, GraphQLNonNull)
    assert isinstance(result["updateFields"].type.of_type.of_type, GraphQLEnumType)

    enum_type: GraphQLEnumType = result["updateFields"].type.of_type.of_type
    assert enum_type.name == "TaskBulkCreateMutationBulkCreateFields"
    assert sorted(enum_type.values) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "name",
        "objective",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]

    assert isinstance(result["uniqueFields"], GraphQLArgument)
    assert result["uniqueFields"].default_value is None
    assert result["uniqueFields"].description is not None
    assert result["uniqueFields"].out_name == "unique_fields"

    assert isinstance(result["uniqueFields"].type, GraphQLList)
    assert isinstance(result["uniqueFields"].type.of_type, GraphQLNonNull)
    assert isinstance(result["uniqueFields"].type.of_type.of_type, GraphQLEnumType)

    enum_type: GraphQLEnumType = result["uniqueFields"].type.of_type.of_type
    assert enum_type.name == "TaskBulkCreateMutationBulkCreateFields"
    assert sorted(enum_type.values) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "name",
        "objective",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]


def test_to_argument_map__mutation_type__bulk_update_mutation():
    class TaskBulkUpdateMutation(MutationType, model=Task):
        name = Input()

    result = convert_to_graphql_argument_map(TaskBulkUpdateMutation, many=True)
    assert sorted(result) == ["batchSize", "input"]

    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLList)
    assert isinstance(result["input"].type.of_type.of_type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type.of_type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.of_type.of_type.name == "TaskBulkUpdateMutation"

    assert isinstance(result["batchSize"], GraphQLArgument)
    assert result["batchSize"].type == GraphQLInt
    assert result["batchSize"].default_value is None
    assert result["batchSize"].description is not None
    assert result["batchSize"].out_name == "batch_size"


def test_to_argument_map__mutation_type__many__delete_mutation():
    class TaskBulkDeleteMutation(MutationType, model=Task): ...

    result = convert_to_graphql_argument_map(TaskBulkDeleteMutation, many=True)
    assert sorted(result) == ["input"]

    assert result["input"] == GraphQLArgument(GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLInt))))


def test_to_argument_map__mutation_type__many__custom_mutation():
    class TaskMutation(MutationType, model=Task): ...

    result = convert_to_graphql_argument_map(TaskMutation, many=True)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLList)
    assert isinstance(result["input"].type.of_type.of_type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type.of_type.of_type, GraphQLInputObjectType)
