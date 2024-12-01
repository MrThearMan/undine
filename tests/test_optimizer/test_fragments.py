import pytest

from example_project.app.models import Person, Project, Task, TaskTypeChoices
from tests.factories import PersonFactory, ProjectFactory, TaskFactory
from undine import Entrypoint, Field, QueryType, create_schema


@pytest.mark.django_db
def test_fragment_spread(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False):
        type = Field()

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

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

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.data == {
        "tasks": [
            {"type": "STORY"},
            {"type": "BUG_FIX"},
        ],
    }


@pytest.mark.django_db
def test_fragment_spread__to_one_relation(graphql, undine_settings):
    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False):
        project = Field(ProjectType)

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

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

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.data == {"tasks": [{"project": {"name": "Foo"}}]}


@pytest.mark.django_db
def test_fragment_spread__to_many_relation(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False):
        assignees = Field(PersonType, many=True)

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

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

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.data == {"tasks": [{"assignees": [{"name": "Foo"}]}]}


@pytest.mark.django_db
def test_fragment_spread__same_relation_in_multiple_fragments(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False):
        name = Field()
        email = Field()

    class TaskType(QueryType, model=Task, auto=False):
        assignees = Field(PersonType, many=True)

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

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

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.data == {
        "tasks": [
            {
                "assignees": [
                    {"name": "Foo", "email": "foo@example.org"},
                ],
            },
        ],
    }


# TODO: When unions are supported `def test_inline_fragment(): ...`
