from __future__ import annotations

import pytest
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Person, Project, Task, TaskTypeChoices
from tests.factories import PersonFactory, ProjectFactory, TaskFactory
from undine import Entrypoint, Field, InterfaceField, InterfaceType, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_optimizer__inline_fragment(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        type = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo", type=TaskTypeChoices.STORY)
    TaskFactory.create(name="bar", type=TaskTypeChoices.BUG_FIX)

    query = """
        query {
          tasks {
            name
            ... {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "foo", "type": "STORY"},
            {"name": "bar", "type": "BUG_FIX"},
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__fragment_spread(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(type=TaskTypeChoices.STORY)
    TaskFactory.create(type=TaskTypeChoices.BUG_FIX)

    query = """
        query {
          tasks {
            ...Type
          }
        }

        fragment Type on TaskType {
          type
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"type": "STORY"},
            {"type": "BUG_FIX"},
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__fragment_spread__query(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(type=TaskTypeChoices.STORY)
    TaskFactory.create(type=TaskTypeChoices.BUG_FIX)

    query = """
        query {
          ...tasks
        }

        fragment tasks on Query {
          tasks {
            type
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"type": "STORY"},
            {"type": "BUG_FIX"},
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__fragment_spread__to_one_relation(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create(name="Foo")
    TaskFactory.create(project=project)

    query = """
        query {
          tasks {
            ...Project
          }
        }

        fragment Project on TaskType {
          project {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"project": {"name": "Foo"}}]}

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__fragment_spread__to_many_relation(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        assignees = Field(PersonType, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person = PersonFactory.create(name="Foo")
    TaskFactory.create(assignees=[person])

    query = """
        query {
          tasks {
            ...Assignee
          }
        }

        fragment Assignee on TaskType {
          assignees {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"assignees": [{"name": "Foo"}]}]}

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__fragment_spread__same_relation_in_multiple_fragments(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()
        email = Field()

    class TaskType(QueryType[Task], auto=False):
        assignees = Field(PersonType, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person = PersonFactory.create(name="Foo", email="foo@example.org")
    TaskFactory.create(assignees=[person])

    query = """
        query {
          tasks {
            ...Name
            ...Email
          }
        }

        fragment Name on TaskType {
          assignees {
            name
          }
        }

        fragment Email on TaskType {
          assignees {
            email
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "assignees": [
                    {"name": "Foo", "email": "foo@example.org"},
                ],
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_ast_walker__fragment_spread__flatten_abstract_type_selections(graphql, undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)
        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="T1", type=TaskTypeChoices.TASK)
    ProjectFactory.create(name="P1")

    query = """
        query {
          named {
            ...NamedFragment
          }
        }

        fragment NamedFragment on Named {
          ... on TaskType {
            type
          }
          ... on ProjectType {
            name
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert len(response.data["named"]) == 2
