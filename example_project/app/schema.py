from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from example_project.app.mutations import CommentCreateMutationType, TaskCreateMutationType, TaskDeleteMutationType
from example_project.app.types import Commentable, CommentType, Named, ReportType, TaskType
from undine import Entrypoint, GQLInfo, RootType, create_schema
from undine.directives import Directive, DirectiveArgument
from undine.optimizer.optimizer import optimize_sync
from undine.pagination import OffsetPagination
from undine.relay import Connection, Node
from undine.subscriptions import ModelDeleteSubscription, ModelSaveSubscription


class VersionDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)
    reports = Entrypoint(ReportType, many=True)
    comments = Entrypoint(CommentType, many=True)

    node = Entrypoint(Node)
    paged_tasks = Entrypoint(Connection(TaskType))

    limited_tasks = Entrypoint(OffsetPagination(TaskType))

    commentable = Entrypoint(Commentable, many=True)
    paged_commentable = Entrypoint(Connection(Commentable))

    named = Entrypoint(Named, many=True)
    paged_named = Entrypoint(Connection(Named))

    @Entrypoint
    def function(self, arg: str = "None") -> list[str]:
        """
        Function docstring.

        :param arg: Argument docstring.
        """
        return [arg]

    task_by_name = Entrypoint(TaskType, nullable=True)

    @task_by_name.resolve
    def resolve_task_by_name(self, info: GQLInfo, name: str) -> Task | None:
        return optimize_sync(Task.objects.all(), info, name=name)


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutationType)
    create_comment = Entrypoint(CommentCreateMutationType)

    delete_task = Entrypoint(TaskDeleteMutationType)

    bulk_create_task = Entrypoint(TaskCreateMutationType, many=True)


class Subscription(RootType):
    @Entrypoint
    async def countdown(self, info: GQLInfo, start: int = 10) -> AsyncGenerator[int, None]:
        for i in range(start, 0, -1):
            await asyncio.sleep(1)
            yield i

    saved_tasks = Entrypoint(ModelSaveSubscription(TaskType))
    deleted_tasks = Entrypoint(ModelDeleteSubscription(TaskType))


schema = create_schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    schema_definition_directives=[VersionDirective(value="v1.0.0")],
)
