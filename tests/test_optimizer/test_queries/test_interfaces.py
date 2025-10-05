from __future__ import annotations

import pytest
from graphql import GraphQLInt, GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task, TaskTypeChoices
from tests.factories import ProjectFactory, TaskFactory
from undine import (
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    InterfaceField,
    InterfaceType,
    Order,
    OrderSet,
    QueryType,
    RootType,
    create_schema,
)


@pytest.mark.django_db
def test_interfaces__entrypoint(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            name
            ... on ProjectType {
              pk
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "pk": project_1.pk,
                "name": "Project 1",
            },
            {
                "name": "Task 1",
                "type": "TASK",
            },
            {
                "pk": project_2.pk,
                "name": "Project 2",
            },
            {
                "name": "Task 2",
                "type": "STORY",
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_interfaces__entrypoint__only_one_fragment(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

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

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "name": "Project 1",
            },
            {
                "name": "Task 1",
                "type": "TASK",
            },
            {
                "name": "Project 2",
            },
            {
                "name": "Task 2",
                "type": "STORY",
            },
        ]
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_interfaces__entrypoint__only_interface_fields(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "name": "Project 1",
            },
            {
                "name": "Task 1",
            },
            {
                "name": "Project 2",
            },
            {
                "name": "Task 2",
            },
        ]
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_interfaces__entrypoint__only_fragment_fields(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            ... on ProjectType {
              pk
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "pk": project_1.pk,
            },
            {
                "type": "TASK",
            },
            {
                "pk": project_2.pk,
            },
            {
                "type": "STORY",
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_interfaces__entrypoint__only_fragment_fields__from_one_fragment(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "type": "TASK",
            },
            {
                "type": "STORY",
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_interfaces__entrypoint__only_fragment_fields__from_one_fragment__typename(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            __typename
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "__typename": "TaskType",
                "type": "TASK",
            },
            {
                "__typename": "TaskType",
                "type": "STORY",
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_interfaces__entrypoint__multiple_interface_fields(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        id = InterfaceField(GraphQLNonNull(GraphQLInt))
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            id
            name
            ... on ProjectType {
              pk
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "id": project_1.pk,
                "pk": project_1.pk,
                "name": "Project 1",
            },
            {
                "id": task_1.pk,
                "name": "Task 1",
                "type": "TASK",
            },
            {
                "id": project_2.pk,
                "pk": project_2.pk,
                "name": "Project 2",
            },
            {
                "id": task_2.pk,
                "name": "Task 2",
                "type": "STORY",
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_interfaces__entrypoint__typename(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        pk = Field()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            __typename
            name
            ... on ProjectType {
              pk
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "__typename": "ProjectType",
                "name": "Project 1",
                "pk": project_1.pk,
            },
            {
                "__typename": "TaskType",
                "name": "Task 1",
                "type": "TASK",
            },
            {
                "__typename": "ProjectType",
                "name": "Project 2",
                "pk": project_2.pk,
            },
            {
                "__typename": "TaskType",
                "name": "Task 2",
                "type": "STORY",
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_interfaces__entrypoint__filtering(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectFilterSet(FilterSet[Project], auto=False):
        name = Filter()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False, filterset=ProjectFilterSet):
        pk = Field()

    class TaskFilterSet(FilterSet[Task], auto=False):
        type = Filter()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False, filterset=TaskFilterSet):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named(
            filterTask: {
              type: TASK
            }
            filterProject: {
              name: "Project 1"
            }
          ) {
            name
            ... on ProjectType {
              pk
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {
                "name": "Project 1",
                "pk": project.pk,
            },
            {
                "name": "Task 1",
                "type": "TASK",
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_interfaces__entrypoint__ordering(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class ProjectOrderSet(OrderSet[Project], auto=False):
        name = Order()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False, orderset=ProjectOrderSet):
        pk = Field()

    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

    class TaskType(QueryType[Task], interfaces=[Named], auto=False, orderset=TaskOrderSet):
        type = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 3")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 3")
    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    query = """
        query {
          named(
            orderByTask: [nameAsc]
            orderByProject: [nameAsc]
          ) {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"name": "Project 1"},
            {"name": "Task 3"},
            {"name": "Project 3"},
            {"name": "Task 1"},
            {"name": "Project 2"},
            {"name": "Task 2"},
        ]
    }

    response.assert_query_count(3)
