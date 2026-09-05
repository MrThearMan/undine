from __future__ import annotations

from graphql import GraphQLNonNull, GraphQLSchema, GraphQLString

from example_project.app.models import Project, Report, Task
from tests.factories import ProjectFactory, ReportFactory, TaskFactory
from undine import Entrypoint, Field, InterfaceField, InterfaceType, QueryType, RootType, UnionType, create_schema
from undine.relay import Connection

__all__ = [
    "create_interface_member_schema",
    "create_one_row_per_member",
    "create_union_member_schema",
]


def create_union_member_schema() -> GraphQLSchema:
    """A schema with a three member `UnionType`, as both a list and a connection `Entrypoint`."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        done = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class ReportType(QueryType[Report], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType, ReportType]): ...

    class Query(RootType):
        commentables = Entrypoint(Commentable, many=True)
        commentable = Entrypoint(Connection(Commentable))

    return create_schema(query=Query)


def create_interface_member_schema() -> GraphQLSchema:
    """A schema with an `InterfaceType` of three implementations, as both a list and a connection `Entrypoint`."""

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()
        done = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class ReportType(QueryType[Report], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        nameds = Entrypoint(Named, many=True)  # type: ignore[arg-type]
        named = Entrypoint(Connection(Named))

    return create_schema(query=Query)


def create_one_row_per_member() -> None:
    """Give every member of the schemas above a single row, so each fetched member costs one query."""
    TaskFactory.create(name="Task 1")
    ProjectFactory.create(name="Project 1")
    ReportFactory.create(name="Report 1")
