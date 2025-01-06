import pytest

from example_project.app.models import Person, Project, Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.optimizer.optimizer import OptimizationData
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_optimizer__add_select_related(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False):
        name = Field()
        project = Field(lambda: ProjectType)

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_select_related("project", query_type=ProjectType)

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="task", project__name="project")

    query = """
        query {
          tasks {
            name
            project {
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
                "name": "task",
                "project": {"name": "project"},
            },
        ],
    }


@pytest.mark.django_db
def test_optimizer__add_prefetch_related(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False):
        name = Field()
        assignees = Field(lambda: PersonType, many=True)

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_prefetch_related("assignees", query_type=PersonType)

    class PersonType(QueryType, model=Person, auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="task", assignees__name="assignee")

    query = """
        query {
          tasks {
            name
            assignees {
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
                "name": "task",
                "assignees": [{"name": "assignee"}],
            },
        ],
    }
