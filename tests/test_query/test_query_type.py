from __future__ import annotations

from inspect import cleandoc

import pytest
from graphql import DirectiveLocation, GraphQLEnumType, GraphQLField, GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, FilterSet, OrderSet, QueryType
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError, MismatchingModelError, MissingModelGenericError
from undine.optimizer.optimizer import OptimizationData
from undine.query import QUERY_TYPE_REGISTRY
from undine.scalars import GraphQLDateTime
from undine.utils.graphql.type_registry import GRAPHQL_REGISTRY


def test_query_type__str() -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    assert str(TaskType) == cleandoc(
        """
        type TaskType {
          name: String!
        }
        """
    )


def test_query_type__registered() -> None:
    assert Task not in QUERY_TYPE_REGISTRY
    assert "MyQueryType" not in GRAPHQL_REGISTRY

    class MyQueryType(QueryType[Task]): ...

    assert Task in QUERY_TYPE_REGISTRY
    assert QUERY_TYPE_REGISTRY[Task] == MyQueryType

    assert "MyQueryType" not in GRAPHQL_REGISTRY

    output_type = MyQueryType.__output_type__()

    assert "MyQueryType" in GRAPHQL_REGISTRY
    assert GRAPHQL_REGISTRY["MyQueryType"] == output_type


def test_query_type__attributes() -> None:
    class MyQueryType(QueryType[Task]):
        """Description."""

    assert MyQueryType.__model__ == Task
    assert MyQueryType.__filterset__ is None
    assert MyQueryType.__orderset__ is None
    assert MyQueryType.__schema_name__ == "MyQueryType"
    assert MyQueryType.__directives__ == []
    assert MyQueryType.__interfaces__ == []
    assert MyQueryType.__extensions__ == {"undine_query_type": MyQueryType}
    assert MyQueryType.__attribute_docstrings__ == {}

    assert sorted(MyQueryType.__field_map__) == [
        "acceptancecriteria_set",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "created_at",
        "demo_url",
        "done",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "name",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]


def test_query_type__output_type() -> None:
    class MyQueryType(QueryType[Task]):
        """Description."""

    output_type = MyQueryType.__output_type__()
    assert output_type.name == "MyQueryType"
    assert output_type.description == "Description."
    assert output_type.is_type_of == MyQueryType.__is_type_of__
    assert output_type.extensions == {"undine_query_type": MyQueryType}

    assert callable(output_type._fields)


def test_query_type__no_model() -> None:
    with pytest.raises(MissingModelGenericError):

        class MyQueryType(QueryType): ...


def test_query_type__is_type_of() -> None:
    class MyQueryType(QueryType[Task]): ...

    assert MyQueryType.__is_type_of__(Task(), mock_gql_info()) is True
    assert MyQueryType.__is_type_of__(Project(), mock_gql_info()) is False


def test_query_type__filterset() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    class MyQueryType(QueryType[Task], filterset=MyFilterSet): ...

    assert MyQueryType.__filterset__ == MyFilterSet


def test_query_type__filterset__different_model() -> None:
    class MyFilterSet(FilterSet[Project]): ...

    with pytest.raises(MismatchingModelError):

        class MyQueryType(QueryType[Task], filterset=MyFilterSet): ...


def test_query_type__orderset() -> None:
    class MyOrderSet(OrderSet[Task]): ...

    class MyQueryType(QueryType[Task], orderset=MyOrderSet): ...

    assert MyQueryType.__orderset__ == MyOrderSet


def test_query_type__orderset__different_model() -> None:
    class MyOrderSet(OrderSet[Project]): ...

    with pytest.raises(MismatchingModelError):

        class MyQueryType(QueryType[Task], orderset=MyOrderSet): ...


def test_query_type__no_auto() -> None:
    class MyQueryType(QueryType[Task], auto=False): ...

    assert MyQueryType.__field_map__ == {}


def test_query_type__exclude() -> None:
    class MyQueryType(QueryType[Task], exclude=["name"]): ...

    assert "name" not in MyQueryType.__field_map__
    assert "pk" in MyQueryType.__field_map__


def test_query_type__exclude__multiple() -> None:
    class MyQueryType(QueryType[Task], exclude=["name", "pk"]): ...

    assert "name" not in MyQueryType.__field_map__
    assert "pk" not in MyQueryType.__field_map__


def test_query_type__dont_register() -> None:
    assert Task not in QUERY_TYPE_REGISTRY

    class MyQueryType(QueryType[Task], register=False): ...

    assert Task not in QUERY_TYPE_REGISTRY


def test_query_type__schema_name() -> None:
    class MyQueryType(QueryType[Task], schema_name="CustomName"): ...

    assert MyQueryType.__schema_name__ == "CustomName"

    output_type = MyQueryType.__output_type__()
    assert output_type.name == "CustomName"


def test_query_type__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.OBJECT], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class MyQueryType(QueryType[Task], directives=directives, auto=False):
        name = Field()

    assert MyQueryType.__directives__ == directives

    assert str(MyQueryType) == cleandoc(
        """
        type MyQueryType @value(value: "foo") {
          name: String!
        }
        """
    )


def test_query_type__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class MyQueryType(QueryType[Task], directives=directives): ...


def test_query_type__directives__decorator() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.OBJECT], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    @ValueDirective(value="foo")
    class MyQueryType(QueryType[Task], auto=False):
        name = Field()

    assert MyQueryType.__directives__ == [ValueDirective(value="foo")]

    assert str(MyQueryType) == cleandoc(
        """
        type MyQueryType @value(value: "foo") {
          name: String!
        }
        """
    )


def test_query_type__extensions() -> None:
    class MyQueryType(QueryType[Task], extensions={"foo": "bar"}): ...

    assert MyQueryType.__extensions__ == {"foo": "bar", "undine_query_type": MyQueryType}


@pytest.mark.django_db
def test_query_type__get_queryset() -> None:
    task = TaskFactory.create(name="Test task")

    class MyQueryType(QueryType[Task]): ...

    qs = MyQueryType.__get_queryset__(info=mock_gql_info())
    assert list(qs) == [task]


@pytest.mark.django_db
def test_query_type__filter_queryset() -> None:
    TaskFactory.create(name="Test task")

    class MyQueryType(QueryType[Task]): ...

    queryset = MyQueryType.__get_queryset__(info=mock_gql_info())
    qs = MyQueryType.__filter_queryset__(queryset=queryset, info=mock_gql_info())
    assert list(qs) == list(queryset)


@pytest.mark.django_db
def test_query_type__permission() -> None:
    task = TaskFactory.create(name="Test task")

    class MyQueryType(QueryType[Task]): ...

    MyQueryType.__permissions__(instance=task, info=mock_gql_info())


def test_query_type__optimizations() -> None:
    class MyQueryType(QueryType[Task]): ...

    info = mock_gql_info()
    data = OptimizationData(model=Task, info=info)

    MyQueryType.__optimizations__(data=data, info=info)


def test_query_type__output_type_field() -> None:
    class MyQueryType(QueryType[Task], auto=False):
        name = Field()
        type = Field()
        created_at = Field()

    output_type = MyQueryType.__output_type__()
    assert sorted(output_type.fields) == ["createdAt", "name", "type"]

    assert isinstance(output_type.fields["createdAt"], GraphQLField)
    assert output_type.fields["createdAt"].type == GraphQLNonNull(GraphQLDateTime)

    assert isinstance(output_type.fields["name"], GraphQLField)
    assert output_type.fields["name"].type == GraphQLNonNull(GraphQLString)

    assert isinstance(output_type.fields["type"], GraphQLField)
    assert isinstance(output_type.fields["type"].type, GraphQLNonNull)
    assert isinstance(output_type.fields["type"].type.of_type, GraphQLEnumType)
    assert sorted(output_type.fields["type"].type.of_type.values) == ["BUG_FIX", "STORY", "TASK"]
