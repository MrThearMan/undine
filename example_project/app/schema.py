from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from example_project.app.mutations import CommentCreateMutationType, TaskCreateMutationType
from example_project.app.types import Commentable, CommentType, Named, ReportType, TaskType
from undine import Entrypoint, RootType, create_schema
from undine.directives import Directive, DirectiveArgument
from undine.relay import Connection, Node

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from undine import GQLInfo


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


class Subscription(RootType):
    @Entrypoint
    async def countdown(self, info: GQLInfo, start: int = 10) -> AsyncGenerator[int, None]:
        for i in range(start, 0, -1):
            await asyncio.sleep(1)
            yield i


schema = create_schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    schema_definition_directives=[VersionDirective(value="v1.0.0")],
)
