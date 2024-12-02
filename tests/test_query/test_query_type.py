import pytest
from graphql import GraphQLEnumType, GraphQLField, GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo, patch_optimizer
from undine import Field, FilterSet, OrderSet, QueryType
from undine.errors.exceptions import MismatchingModelError, MissingModelError
from undine.optimizer.optimizer import OptimizationProcessor
from undine.registies import GRAPHQL_TYPE_REGISTRY, QUERY_TYPE_REGISTRY
from undine.resolvers import ModelManyResolver, ModelSingleResolver
from undine.scalars import GraphQLDate


def test_query_type__registered():
    assert Task not in QUERY_TYPE_REGISTRY
    assert "MyQueryType" not in GRAPHQL_TYPE_REGISTRY

    class MyQueryType(QueryType, model=Task): ...

    assert Task in QUERY_TYPE_REGISTRY
    assert QUERY_TYPE_REGISTRY[Task] == MyQueryType

    assert "MyQueryType" not in GRAPHQL_TYPE_REGISTRY

    output_type = MyQueryType.__output_type__()

    assert "MyQueryType" in GRAPHQL_TYPE_REGISTRY
    assert GRAPHQL_TYPE_REGISTRY["MyQueryType"] == output_type


def test_query_type__attributes():
    class MyQueryType(QueryType, model=Task):
        """Description."""

    assert MyQueryType.__model__ == Task
    assert MyQueryType.__filterset__ is None
    assert MyQueryType.__orderset__ is None
    assert MyQueryType.__lookup_field__ == "pk"
    assert MyQueryType.__typename__ == "MyQueryType"
    assert MyQueryType.__extensions__ == {"undine_type": MyQueryType}

    assert sorted(MyQueryType.__field_map__) == [
        "acceptancecriteria",
        "assignees",
        "comments",
        "created_at",
        "name",
        "objective",
        "pk",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]


def test_query_type__output_type():
    class MyQueryType(QueryType, model=Task):
        """Description."""

    output_type = MyQueryType.__output_type__()
    assert output_type.name == "MyQueryType"
    assert output_type.description == "Description."
    assert output_type.is_type_of == MyQueryType.__is_type_of__
    assert output_type.extensions == {"undine_type": MyQueryType}

    assert callable(output_type._fields)


def test_query_type__no_model():
    with pytest.raises(MissingModelError):

        class MyQueryType(QueryType): ...


def test_query_type__is_type_of():
    class MyQueryType(QueryType, model=Task): ...

    assert MyQueryType.__is_type_of__(Task(), MockGQLInfo()) is True
    assert MyQueryType.__is_type_of__(Project(), MockGQLInfo()) is False


def test_query_type__filterset():
    class MyFilterSet(FilterSet, model=Task): ...

    class MyQueryType(QueryType, model=Task, filterset=MyFilterSet): ...

    assert MyQueryType.__filterset__ == MyFilterSet


def test_query_type__filterset__default():
    class MyQueryType(QueryType, model=Task, filterset=True): ...

    assert MyQueryType.__filterset__ is not None
    assert MyQueryType.__filterset__.__name__ == "TaskFilterSet"
    assert MyQueryType.__filterset__.__model__ == Task


def test_query_type__filterset__different_model():
    class MyFilterSet(FilterSet, model=Project): ...

    with pytest.raises(MismatchingModelError):

        class MyQueryType(QueryType, model=Task, filterset=MyFilterSet): ...


def test_query_type__orderset():
    class MyOrderSet(OrderSet, model=Task): ...

    class MyQueryType(QueryType, model=Task, orderset=MyOrderSet): ...

    assert MyQueryType.__orderset__ == MyOrderSet


def test_query_type__orderset__default():
    class MyQueryType(QueryType, model=Task, orderset=True): ...

    assert MyQueryType.__orderset__ is not None
    assert MyQueryType.__orderset__.__name__ == "TaskOrderSet"
    assert MyQueryType.__orderset__.__model__ == Task


def test_query_type__orderset__different_model():
    class MyOrderSet(OrderSet, model=Project): ...

    with pytest.raises(MismatchingModelError):

        class MyQueryType(QueryType, model=Task, orderset=MyOrderSet): ...


def test_query_type__lookup_field():
    class MyQueryType(QueryType, model=Task, lookup_field="name"): ...

    assert MyQueryType.__lookup_field__ == "name"


def test_query_type__no_auto():
    class MyQueryType(QueryType, model=Task, auto=False): ...

    assert MyQueryType.__field_map__ == {}


def test_query_type__exclude():
    class MyQueryType(QueryType, model=Task, exclude=["name"]): ...

    assert "name" not in MyQueryType.__field_map__
    assert "pk" in MyQueryType.__field_map__


def test_query_type__exclude__multiple():
    class MyQueryType(QueryType, model=Task, exclude=["name", "pk"]): ...

    assert "name" not in MyQueryType.__field_map__
    assert "pk" not in MyQueryType.__field_map__


def test_query_type__dont_register():
    assert Task not in QUERY_TYPE_REGISTRY

    class MyQueryType(QueryType, model=Task, register=False): ...

    assert Task not in QUERY_TYPE_REGISTRY


def test_query_type__typename():
    class MyQueryType(QueryType, model=Task, typename="CustomName"): ...

    assert MyQueryType.__typename__ == "CustomName"

    output_type = MyQueryType.__output_type__()
    assert output_type.name == "CustomName"


@pytest.mark.django_db
def test_query_type__get_queryset():
    task = TaskFactory.create(name="Test task")

    class MyQueryType(QueryType, model=Task): ...

    qs = MyQueryType.__get_queryset__(info=MockGQLInfo())
    assert list(qs) == [task]


@pytest.mark.django_db
def test_query_type__filter_queryset():
    TaskFactory.create(name="Test task")

    class MyQueryType(QueryType, model=Task): ...

    queryset = MyQueryType.__get_queryset__(info=MockGQLInfo())
    qs = MyQueryType.__filter_queryset__(queryset=queryset, info=MockGQLInfo())
    assert list(qs) == list(queryset)


@pytest.mark.django_db
def test_query_type__permission_single():
    task = TaskFactory.create(name="Test task")

    class MyQueryType(QueryType, model=Task): ...

    assert MyQueryType.__permission_single__(instance=task, info=MockGQLInfo()) is True


@pytest.mark.django_db
def test_query_type__permission_many():
    TaskFactory.create(name="Test task")

    class MyQueryType(QueryType, model=Task): ...

    queryset = MyQueryType.__get_queryset__(info=MockGQLInfo())
    assert MyQueryType.__permission_many__(queryset=queryset, info=MockGQLInfo()) is True


def test_query_type__optimizer_hook():
    class MyQueryType(QueryType, model=Task): ...

    processor = OptimizationProcessor(query_type=MyQueryType, info=MockGQLInfo())

    MyQueryType.__optimizer_hook__(processor=processor)


@pytest.mark.django_db
def test_query_type__resolve_one():
    task = TaskFactory.create(name="Test task")

    class MyQueryType(QueryType, model=Task): ...

    resolver = ModelSingleResolver(query_type=MyQueryType)

    with patch_optimizer():
        result = resolver(root=None, info=MockGQLInfo(), pk=task.pk)

    assert result == task


@pytest.mark.django_db
def test_query_type__resolve_many():
    task = TaskFactory.create(name="Test task")

    class MyQueryType(QueryType, model=Task): ...

    resolver = ModelManyResolver(query_type=MyQueryType)

    with patch_optimizer():
        qs = resolver(root=task, info=MockGQLInfo())

    assert list(qs) == [task]


def test_query_type__output_type_field():
    class MyQueryType(QueryType, model=Task, auto=False):
        name = Field()
        type = Field()
        created_at = Field()

    output_type = MyQueryType.__output_type__()
    assert sorted(output_type.fields) == ["createdAt", "name", "type"]

    assert isinstance(output_type.fields["createdAt"], GraphQLField)
    assert output_type.fields["createdAt"].type == GraphQLNonNull(GraphQLDate)

    assert isinstance(output_type.fields["name"], GraphQLField)
    assert output_type.fields["name"].type == GraphQLNonNull(GraphQLString)

    assert isinstance(output_type.fields["type"], GraphQLField)
    assert isinstance(output_type.fields["type"].type, GraphQLNonNull)
    assert isinstance(output_type.fields["type"].type.of_type, GraphQLEnumType)
    assert sorted(output_type.fields["type"].type.of_type.values) == ["BUG_FIX", "STORY", "TASK"]
