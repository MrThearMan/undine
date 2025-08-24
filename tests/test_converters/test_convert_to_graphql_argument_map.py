from __future__ import annotations

from typing import TypedDict

from django.db.models import Subquery, Value
from django.db.models.functions.datetime import Now
from graphql import (
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLString,
    Undefined,
)

from example_project.app.models import Comment, Project, Task
from undine import (
    Calculation,
    CalculationArgument,
    DjangoExpression,
    FilterSet,
    GQLInfo,
    Input,
    MutationType,
    OrderSet,
    QueryType,
)
from undine.converters import convert_to_graphql_argument_map
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.utils.reflection import get_signature


def test_to_argument_map__function__type() -> None:
    def func(arg: str, one_two: int) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result == {
        "arg": GraphQLArgument(GraphQLNonNull(GraphQLString), out_name="arg"),
        "oneTwo": GraphQLArgument(GraphQLNonNull(GraphQLInt), out_name="one_two"),
    }


def test_to_argument_map__function__type__nullable() -> None:
    def func(arg: str | None) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert sorted(result) == ["arg"]
    assert isinstance(result["arg"], GraphQLArgument)
    assert result["arg"].type == GraphQLString


def test_to_argument_map__function__default_value() -> None:
    def func(arg: str = "foo") -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].default_value == "foo"


def test_to_argument_map__function__default_value__none() -> None:
    def func(arg: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].default_value is Undefined


def test_to_argument_map__function__description() -> None:
    def func(arg: str) -> int:
        """
        Description.

        :param arg: Argument description.
        """

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].description == "Argument description."


def test_to_argument_map__function__description__none() -> None:
    def func(arg: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].description is None


def test_to_argument_map__function__deprecation_reason() -> None:
    def func(arg: str) -> int:
        """
        Description.

        :deprecated arg: Use something else.
        """

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].deprecation_reason == "Use something else."


def test_to_argument_map__function__deprecation_reason__none() -> None:
    def func(arg: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert result["arg"].deprecation_reason is None


def test_to_argument_map__function__schema_name() -> None:
    def func(new_argument: str) -> int: ...

    result = convert_to_graphql_argument_map(func, many=False)
    assert sorted(result) == ["newArgument"]


def test_to_argument_map__function__typed_dict() -> None:
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

    assert result["arg"].type.of_type.name == "UserParamsInput"

    assert sorted(result["arg"].type.of_type.fields) == ["age", "name"]

    assert result["arg"].type.of_type.fields["age"].type == GraphQLInt
    assert result["arg"].type.of_type.fields["name"].type == GraphQLNonNull(GraphQLString)


def test_to_argument_map__model_field() -> None:
    field = Task._meta.get_field("name")
    assert convert_to_graphql_argument_map(field, many=False) == {}


def test_to_argument_map__related_field() -> None:
    field = Task._meta.get_field("project")
    assert convert_to_graphql_argument_map(field, many=False) == {}


def test_to_argument_map__expression() -> None:
    assert convert_to_graphql_argument_map(Now(), many=False) == {}


def test_to_argument_map__subquery() -> None:
    sq = Subquery(Task.objects.values("id"))
    assert convert_to_graphql_argument_map(sq, many=False) == {}


def test_to_argument_map__lazy_relation__single() -> None:
    class ProjectType(QueryType[Project]): ...

    lazy = LazyRelation(field=Task._meta.get_field("project"))

    assert convert_to_graphql_argument_map(lazy, many=False) == {}


def test_to_argument_map__lazy_relation__many() -> None:
    class ProjectFilterSet(FilterSet[Project]): ...

    class ProjectOrderSet(OrderSet[Project]): ...

    class ProjectType(QueryType[Project], filterset=ProjectFilterSet, orderset=ProjectOrderSet): ...

    lazy = LazyRelation(field=Task._meta.get_field("project"))

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


def test_to_argument_map__lazy_lambda() -> None:
    class ProjectFilterSet(FilterSet[Project]): ...

    class ProjectOrderSet(OrderSet[Project]): ...

    class ProjectType(QueryType[Project], filterset=ProjectFilterSet, orderset=ProjectOrderSet): ...

    lazy = LazyLambda(callback=lambda: ProjectType)

    result = convert_to_graphql_argument_map(lazy, many=True)
    assert sorted(result) == ["filter", "orderBy"]


def test_to_argument_map__lazy_generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")
    lazy = LazyGenericForeignKey(field)
    assert convert_to_graphql_argument_map(lazy, many=False) == {}


def test_to_argument_map__type_ref() -> None:
    ref = TypeRef(value=int)

    result = convert_to_graphql_argument_map(ref)
    assert sorted(result) == []


def test_to_argument_map__query_type() -> None:
    class TaskFilterSet(FilterSet[Task]): ...

    class TaskOrderSet(OrderSet[Task]): ...

    class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet): ...

    assert convert_to_graphql_argument_map(TaskType, many=False) == {}


def test_to_argument_map__query_type__entrypoint() -> None:
    class TaskFilterSet(FilterSet[Task]): ...

    class TaskOrderSet(OrderSet[Task]): ...

    class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet): ...

    results = convert_to_graphql_argument_map(TaskType, many=False, entrypoint=True)

    assert sorted(results) == ["pk"]
    assert isinstance(results["pk"], GraphQLArgument)
    assert results["pk"].type == GraphQLNonNull(GraphQLInt)


def test_to_argument_map__query_type__many() -> None:
    class TaskFilterSet(FilterSet[Task]): ...

    class TaskOrderSet(OrderSet[Task]): ...

    class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet): ...

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


def test_to_argument_map__query_type__many__entrypoint() -> None:
    class TaskFilterSet(FilterSet[Task]): ...

    class TaskOrderSet(OrderSet[Task]): ...

    class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet): ...

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


def test_to_argument_map__query_type__many__no_filterset_or_orderset() -> None:
    class TaskType(QueryType[Task]): ...

    assert convert_to_graphql_argument_map(TaskType, many=True) == {}


def test_to_argument_map__mutation_type__create_mutation() -> None:
    class TaskCreateMutation(MutationType[Task]):
        name = Input()

    result = convert_to_graphql_argument_map(TaskCreateMutation, many=False)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.name == "TaskCreateMutation"

    assert result["input"].type.of_type.fields["name"].type == GraphQLNonNull(GraphQLString)


def test_to_argument_map__mutation_type__create_mutation__entrypoint() -> None:
    class TaskCreateMutation(MutationType[Task]):
        name = Input()

    result = convert_to_graphql_argument_map(TaskCreateMutation, many=False, entrypoint=True)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.name == "TaskCreateMutation"

    assert result["input"].type.of_type.fields["name"].type == GraphQLNonNull(GraphQLString)


def test_to_argument_map__mutation_type__update_mutation() -> None:
    class TaskUpdateMutation(MutationType[Task]):
        name = Input()

    result = convert_to_graphql_argument_map(TaskUpdateMutation, many=False)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.name == "TaskUpdateMutation"

    assert result["input"].type.of_type.fields["name"].type == GraphQLString


def test_to_argument_map__mutation_type__update_mutation__entrypoint() -> None:
    class TaskUpdateMutation(MutationType[Task]):
        name = Input()

    result = convert_to_graphql_argument_map(TaskUpdateMutation, many=False, entrypoint=True)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.name == "TaskUpdateMutation"

    assert result["input"].type.of_type.fields["name"].type == GraphQLString


def test_to_argument_map__mutation_type__delete_mutation() -> None:
    class TaskDeleteMutation(MutationType[Task]): ...

    result = convert_to_graphql_argument_map(TaskDeleteMutation, many=False)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.fields["pk"].type == GraphQLNonNull(GraphQLInt)


def test_to_argument_map__mutation_type__custom_mutation() -> None:
    class TaskCreateMutation(MutationType[Task]): ...

    result = convert_to_graphql_argument_map(TaskCreateMutation, many=False)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLInputObjectType)


def test_to_argument_map__mutation_type__bulk_create_mutation() -> None:
    class TaskBulkCreateMutation(MutationType[Task]):
        name = Input()

    result = convert_to_graphql_argument_map(TaskBulkCreateMutation, many=True)

    assert sorted(result) == ["input"]

    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLList)
    assert isinstance(result["input"].type.of_type.of_type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type.of_type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.of_type.of_type.name == "TaskBulkCreateMutation"


def test_to_argument_map__mutation_type__bulk_update_mutation() -> None:
    class TaskBulkUpdateMutation(MutationType[Task]):
        name = Input()

    result = convert_to_graphql_argument_map(TaskBulkUpdateMutation, many=True)
    assert sorted(result) == ["input"]

    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLList)
    assert isinstance(result["input"].type.of_type.of_type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type.of_type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.of_type.of_type.name == "TaskBulkUpdateMutation"


def test_to_argument_map__mutation_type__many__delete_mutation() -> None:
    class TaskBulkDeleteMutation(MutationType[Task]): ...

    result = convert_to_graphql_argument_map(TaskBulkDeleteMutation, many=True)
    assert sorted(result) == ["input"]

    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLList)
    assert isinstance(result["input"].type.of_type.of_type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type.of_type.of_type, GraphQLInputObjectType)

    assert result["input"].type.of_type.of_type.of_type.fields["pk"].type == GraphQLNonNull(GraphQLInt)


def test_to_argument_map__mutation_type__many__custom_mutation() -> None:
    class TaskCreateMutation(MutationType[Task]): ...

    result = convert_to_graphql_argument_map(TaskCreateMutation, many=True)

    assert sorted(result) == ["input"]
    assert isinstance(result["input"], GraphQLArgument)
    assert isinstance(result["input"].type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type, GraphQLList)
    assert isinstance(result["input"].type.of_type.of_type, GraphQLNonNull)
    assert isinstance(result["input"].type.of_type.of_type.of_type, GraphQLInputObjectType)


def test_to_argument_map__calculated() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    args = convert_to_graphql_argument_map(ExampleCalculation, many=False)

    assert args == {
        "value": GraphQLArgument(
            GraphQLNonNull(GraphQLInt),
            default_value=Undefined,
            description=None,
            out_name="value",
            extensions={"undine_calculation_argument": ExampleCalculation.value},
        ),
    }


def test_to_argument_map__calculated__nullable() -> None:
    class ExampleCalculation(Calculation[int]):
        value = CalculationArgument(int | None)

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    args = convert_to_graphql_argument_map(ExampleCalculation, many=False)

    assert args == {
        "value": GraphQLArgument(
            GraphQLInt,
            default_value=Undefined,
            description=None,
            out_name="value",
            extensions={"undine_calculation_argument": ExampleCalculation.value},
        ),
    }
