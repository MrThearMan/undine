from __future__ import annotations

from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from example_project.app.mutations import CommentCreateMutationType, TaskCreateMutationType
from example_project.app.types import Commentable, CommentType, Named, ReportType, TaskType
from undine import Entrypoint, RootType, create_schema
from undine.directives import Directive, DirectiveArgument
from undine.relay import Connection, Node


class VersionDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)
    reports = Entrypoint(ReportType, many=True)
    comments = Entrypoint(CommentType, many=True)

    node = Entrypoint(Node)
    paged_tasks = Entrypoint(Connection(TaskType))

    named = Entrypoint(Named, many=True)
    """All named objects."""

    commentable = Entrypoint(Commentable, many=True)
    paged_commentable = Entrypoint(Connection(Commentable))  # WIP

    @Entrypoint
    def function(self, arg: str = "None") -> list[str]:
        """
        Function docstring.

        :param arg: Argument docstring.
        """
        return [arg]


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutationType)
    create_comment = Entrypoint(CommentCreateMutationType)

    bulk_create_task = Entrypoint(TaskCreateMutationType, many=True)


schema = create_schema(
    query=Query,
    mutation=Mutation,
    schema_definition_directives=[VersionDirective(value="v1.0.0")],
)
