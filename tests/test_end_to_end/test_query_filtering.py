from __future__ import annotations

from typing import NotRequired, TypedDict

import pytest
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When

from example_project.app.models import Person, Task
from tests.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory
from undine import (
    Calculation,
    CalculationArgument,
    DjangoExpression,
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    QueryType,
    RootType,
    create_schema,
)
from undine.exceptions import EmptyFilterResult
from undine.utils.graphql.utils import get_arguments


@pytest.mark.django_db
def test_end_to_end__filtering(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        name_startswith = Filter("name", lookup="startswith")

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(filter: {nameStartswith: "b"}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "bar"},
            {"name": "baz"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__nested(graphql, undine_settings) -> None:
    class PersonFilterSet(FilterSet[Person], auto=False):
        name = Filter()

    class PersonType(QueryType[Person], auto=False, filterset=PersonFilterSet):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    PersonFactory.create(name="foo", tasks=[task_1])
    PersonFactory.create(name="bar", tasks=[task_1])
    PersonFactory.create(name="foo", tasks=[task_2])
    PersonFactory.create(name="bar", tasks=[task_2])

    query = """
        query {
          tasks {
            name
            assignees(filter: {name: "foo"}) {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "foo",
                "assignees": [
                    {"name": "foo"},
                ],
            },
            {
                "name": "bar",
                "assignees": [
                    {"name": "foo"},
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__get_arguments(graphql, undine_settings) -> None:
    person_args = {}
    task_args = {}

    class PersonFilterSet(FilterSet[Person], auto=False):
        name = Filter()

        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
            nonlocal person_args
            person_args = get_arguments(info)
            return queryset

    class PersonType(QueryType[Person], auto=False, filterset=PersonFilterSet):
        name = Field()

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()

        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
            nonlocal task_args
            task_args = get_arguments(info)
            return queryset

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    PersonFactory.create(name="foo", tasks=[task_1])
    PersonFactory.create(name="bar", tasks=[task_1])
    PersonFactory.create(name="foo", tasks=[task_2])
    PersonFactory.create(name="bar", tasks=[task_2])

    query = """
        query {
          tasks(filter: {name: "bar"}) {
            name
            assignees(filter: {name: "foo"}) {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "bar",
                "assignees": [
                    {"name": "foo"},
                ],
            },
        ],
    }

    assert person_args == {"filter": {"name": "foo"}}
    assert task_args == {"filter": {"name": "bar"}}


@pytest.mark.django_db
def test_end_to_end__filtering__many__match_any(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        name_startswith_any = Filter("name", lookup="startswith", many=True)

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(filter: {nameStartswithAny: ["f", "b"]}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "foo"},
            {"name": "bar"},
            {"name": "baz"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__many__match_all(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        name_contains_all = Filter("name", lookup="contains", many=True, match="all")

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(filter: {nameContainsAll: ["b", "r"]}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "bar"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__distinct(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        assignee_name_contains = Filter("assignees__name", lookup="contains", distinct=True)

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assignee_1 = PersonFactory.create(name="foo")
    assignee_2 = PersonFactory.create(name="bar")
    assignee_3 = PersonFactory.create(name="baz")
    assignee_4 = PersonFactory.create(name="fizz")
    assignee_5 = PersonFactory.create(name="buzz")

    TaskFactory.create(name="one", assignees=[assignee_1, assignee_4, assignee_5])
    TaskFactory.create(name="two", assignees=[assignee_2, assignee_3, assignee_5])

    query = """
        query {
          tasks(filter: {assigneeNameContains: "z"}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "one"},
            {"name": "two"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__distinct_missing(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        assignee_name_contains = Filter("assignees__name", lookup="contains")

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assignee_1 = PersonFactory.create(name="foo")
    assignee_2 = PersonFactory.create(name="bar")
    assignee_3 = PersonFactory.create(name="baz")
    assignee_4 = PersonFactory.create(name="fizz")
    assignee_5 = PersonFactory.create(name="buzz")

    TaskFactory.create(name="one", assignees=[assignee_1, assignee_4, assignee_5])
    TaskFactory.create(name="two", assignees=[assignee_2, assignee_3, assignee_5])

    query = """
        query {
          tasks(filter: {assigneeNameContains: "z"}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # Data is duplicated because we are misssing `distinct` from the filter.
    assert response.data == {
        "tasks": [
            {"name": "one"},
            {"name": "one"},
            {"name": "two"},
            {"name": "two"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__lookup_changes_input_type(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        no_project = Filter("project", lookup="isnull")

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create()

    TaskFactory.create(name="foo", project=project)
    TaskFactory.create(name="bar", project=None)
    TaskFactory.create(name="baz", project=project)

    query = """
        query {
          tasks(filter: {noProject: true}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "bar"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__q_value(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        has_project = Filter(Q(project__isnull=False))

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create()

    TaskFactory.create(name="foo", project=project)
    TaskFactory.create(name="bar", project=None)
    TaskFactory.create(name="baz", project=project)

    query = """
        query {
          tasks(filter: {hasProject: true}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "foo"},
            {"name": "baz"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__q_value__negated(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        no_project = Filter(~Q(project__isnull=False))

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create()

    TaskFactory.create(name="foo", project=project)
    TaskFactory.create(name="bar", project=None)
    TaskFactory.create(name="baz", project=project)

    query = """
        query {
          tasks(filter: {noProject: true}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "bar"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__function(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        @Filter(distinct=True)
        def has_commented(self: Filter, info: GQLInfo, value: bool) -> Q:  # noqa: FBT001
            user = info.context.user
            if user.is_anonymous:  # pragma: no cover
                raise EmptyFilterResult
            condition = Q(comments__commenter__name=user.username)
            return condition if value else ~condition

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    CommentFactory.create(commenter__name="admin", target=task_1)
    CommentFactory.create(commenter__name="admin", target=task_1)
    CommentFactory.create(commenter__name="regular", target=task_1)
    CommentFactory.create(commenter__name="regular", target=task_2)

    query = """
        query {
          tasks(filter: {hasCommented: true}) {
            name
          }
        }
    """

    graphql.login_with_superuser(username="admin")
    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "foo"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__function__empty_filter_results(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        @Filter
        def none(self: Filter, value: bool) -> Q:  # noqa: FBT001
            raise EmptyFilterResult

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(filter: {none: true}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__logical_operators(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        name_startswith = Filter("name", lookup="startswith")
        name_endswith = Filter("name", lookup="endswith")

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(filter: {OR: {nameStartswith: "b", nameEndswith: "o"}}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "foo"},
            {"name": "bar"},
            {"name": "baz"},
        ],
    }


def setup_optimizer__filtering__function__typed_dict(undine_settings) -> None:
    class NameFilterInput(TypedDict):
        begin: str
        ends: NotRequired[str]

    class TaskFilterSet(FilterSet[Task], auto=False):
        @Filter
        def custom(self: Filter, value: NameFilterInput) -> Q:
            condition = Q(name__startswith=value["begin"])
            if value.get("ends") is not None:
                condition &= Q(name__endswith=value["ends"])
            return condition

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)


@pytest.mark.django_db
def test_end_to_end__filtering__function__typed_dict(graphql, undine_settings) -> None:
    setup_optimizer__filtering__function__typed_dict(undine_settings)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(filter: {custom: {begin: "b", ends: "r"}}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "bar"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__function__typed_dict__not_required(graphql, undine_settings) -> None:
    setup_optimizer__filtering__function__typed_dict(undine_settings)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(filter: {custom: {begin: "b"}}) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "bar"},
            {"name": "baz"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__calculated_field(graphql, undine_settings) -> None:
    class ExampleCalculation(Calculation[int]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Case(
                When(name="foo", then=Value(None)),
                default=Value(self.value),
                output_field=IntegerField(null=True),
            )

    class TaskFilterSet(FilterSet[Task], auto=False):
        @Filter
        def only_numbered(self: Filter, *, value: bool) -> Q:
            return ~Q(calculated_number=None) if value else Q()

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()
        calculated_number = Field(ExampleCalculation)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(
            filter: {
              onlyNumbered: true
            }
          ) {
            name
            calculatedNumber(value: 1)
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "bar",
                "calculatedNumber": 1,
            },
            {
                "name": "baz",
                "calculatedNumber": 1,
            },
        ],
    }


@pytest.mark.django_db
def test_end_to_end__filtering__max_filters(graphql, undine_settings) -> None:
    class TaskFilterSet(FilterSet[Task], auto=False):
        name_startswith = Filter("name", lookup="startswith")
        name_endswith = Filter("name", lookup="endswith")

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)
    undine_settings.MAX_FILTERS_PER_TYPE = 1

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks(
            filter: {
              nameStartswith: "b"
              nameEndswith: "r"
            }
          ) {
            name
          }
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "'TaskFilterSet' received 2 filters which is more than the maximum allowed of 1.",
            "extensions": {
                "status_code": 400,
                "error_code": "TOO_MANY_FILTERS",
            },
            "path": ["tasks"],
        }
    ]
