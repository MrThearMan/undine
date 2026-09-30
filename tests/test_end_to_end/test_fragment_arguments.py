from __future__ import annotations

import pytest
from django.db.models import Value

from example_project.app.models import Person, Project, Task
from tests.factories import PersonFactory, ProjectFactory, TaskFactory
from undine import (
    Calculation,
    CalculationArgument,
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    QueryType,
    RootType,
    UnionType,
    create_schema,
)
from undine.pagination import OffsetPagination
from undine.typing import DjangoExpression


class Multiplied(Calculation[int]):
    factor = CalculationArgument(int)

    def __call__(self, info: GQLInfo) -> DjangoExpression:
        return Value(self.factor * 2)


def create_example_schema():
    class PersonFilterSet(FilterSet[Person], auto=False):
        name = Filter()

    class PersonType(QueryType[Person], auto=False, filterset=PersonFilterSet):
        name = Field()

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        name = Field()
        assignees = Field(PersonType)
        multiplied = Field(Multiplied)

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)
        searchables = Entrypoint(OffsetPagination(Searchable))  # type: ignore[arg-type]

    return create_schema(query=Query)


@pytest.fixture
def example_data() -> None:
    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")
    PersonFactory.create(name="alice", tasks=[task_1, task_2])
    PersonFactory.create(name="bob", tasks=[task_1])
    ProjectFactory.create(name="baz")


@pytest.mark.django_db
def test_fragment_arguments__nested_filter(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query {
          tasks {
            ...TaskFields(personName: "alice")
          }
        }

        fragment TaskFields($personName: String) on TaskType {
          name
          assignees(filter: {name: $personName}) {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.json == {
        "data": {
            "tasks": [
                {"name": "foo", "assignees": [{"name": "alice"}]},
                {"name": "bar", "assignees": [{"name": "alice"}]},
            ],
        },
    }
    assert len(response.queries) == 2


@pytest.mark.django_db
def test_fragment_arguments__entrypoint_filter(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query {
          ...QueryFields(taskName: "foo")
        }

        fragment QueryFields($taskName: String) on Query {
          tasks(filter: {name: $taskName}) {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.json == {"data": {"tasks": [{"name": "foo"}]}}
    assert len(response.queries) == 1


@pytest.mark.django_db
def test_fragment_arguments__include(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query {
          tasks {
            ...TaskFields(withAssignees: false)
          }
        }

        fragment TaskFields($withAssignees: Boolean!) on TaskType {
          name
          assignees @include(if: $withAssignees) {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.json == {"data": {"tasks": [{"name": "foo"}, {"name": "bar"}]}}
    # Assignees are not prefetched, since they are not included.
    assert len(response.queries) == 1


@pytest.mark.django_db
def test_fragment_arguments__nested_fragments(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query {
          tasks {
            ...TaskFields(personName: "bob")
          }
        }

        fragment TaskFields($personName: String) on TaskType {
          name
          ...AssigneeFields(name: $personName)
        }

        fragment AssigneeFields($name: String) on TaskType {
          assignees(filter: {name: $name}) {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.json == {
        "data": {
            "tasks": [
                {"name": "foo", "assignees": [{"name": "bob"}]},
                {"name": "bar", "assignees": []},
            ],
        },
    }
    assert len(response.queries) == 2


@pytest.mark.django_db
def test_fragment_arguments__default_value(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query {
          tasks {
            ...TaskFields
          }
        }

        fragment TaskFields($personName: String = "bob") on TaskType {
          name
          assignees(filter: {name: $personName}) {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.json == {
        "data": {
            "tasks": [
                {"name": "foo", "assignees": [{"name": "bob"}]},
                {"name": "bar", "assignees": []},
            ],
        },
    }
    assert len(response.queries) == 2


@pytest.mark.django_db
def test_fragment_arguments__operation_variable(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query ($name: String) {
          tasks {
            ...TaskFields(personName: $name)
          }
        }

        fragment TaskFields($personName: String) on TaskType {
          name
          assignees(filter: {name: $personName}) {
            name
          }
        }
    """

    response = graphql(query, variables={"name": "bob"}, count_queries=True)

    assert response.json == {
        "data": {
            "tasks": [
                {"name": "foo", "assignees": [{"name": "bob"}]},
                {"name": "bar", "assignees": []},
            ],
        },
    }
    assert len(response.queries) == 2


@pytest.mark.django_db
def test_fragment_arguments__calculation(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query {
          tasks {
            ...TaskFields(factor: 3)
          }
        }

        fragment TaskFields($factor: Int!) on TaskType {
          name
          multiplied(factor: $factor)
        }
    """

    response = graphql(query, count_queries=True)

    assert response.json == {
        "data": {
            "tasks": [
                {"name": "foo", "multiplied": 6},
                {"name": "bar", "multiplied": 6},
            ],
        },
    }
    assert len(response.queries) == 1


@pytest.mark.django_db
def test_fragment_arguments__union_offset_pagination(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = True
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query {
          ...QueryFields(limit: 2, withName: true)
        }

        fragment QueryFields($limit: Int, $withName: Boolean!) on Query {
          searchables(limit: $limit) {
            __typename
            ... on TaskType {
              name @include(if: $withName)
            }
            ... on ProjectType {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.json == {
        "data": {
            "searchables": [
                {"__typename": "ProjectType", "name": "baz"},
                {"__typename": "TaskType", "name": "foo"},
            ],
        },
    }


@pytest.mark.django_db
def test_fragment_arguments__not_enabled(graphql, undine_settings, example_data) -> None:
    undine_settings.EXPERIMENTAL_FRAGMENT_ARGUMENTS = False
    undine_settings.SCHEMA = create_example_schema()

    query = """
        query {
          tasks {
            ...TaskFields(personName: "alice")
          }
        }

        fragment TaskFields($personName: String) on TaskType {
          name
        }
    """

    response = graphql(query, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Syntax Error: Expected Name, found '('.",
                "locations": [{"line": 4, "column": 26}],
                "extensions": {"status_code": 400},
            },
        ],
    }
