from __future__ import annotations

from typing import TYPE_CHECKING

from example_project.app.models import Person, Project, Task, TaskResult, Team
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.relay import Connection

if TYPE_CHECKING:
    from graphql import GraphQLSchema


__all__ = [
    "create_list_nesting_connection_schema",
    "create_list_nesting_schema",
]


def create_list_nesting_schema() -> GraphQLSchema:
    """Create a schema with both to-one and to-many relations for testing list nesting depth."""

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TeamType(QueryType[Team], auto=False):
        name = Field()
        members = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        team = Field()

    class TaskResultType(QueryType[TaskResult], auto=False):
        details = Field()
        task = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()
        result = Field()
        assignees = Field()
        related_tasks = Field()

        @Field
        def tags(self) -> list[str]:
            return []

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)
        people = Entrypoint(PersonType, many=True)

    return create_schema(query=Query)


def create_list_nesting_connection_schema() -> GraphQLSchema:
    """Create a schema where the to-many relations are Relay connections."""

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(Connection(PersonType))

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    return create_schema(query=Query)
