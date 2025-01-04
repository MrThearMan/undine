from __future__ import annotations

from example_project.app.mutations import TaskCreateMutationType
from example_project.app.types import ReportType, TaskType
from undine import Entrypoint, RootOperationType, create_schema
from undine.relay import Connection, Node


class Query(RootOperationType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)
    reports = Entrypoint(ReportType, many=True)

    node = Entrypoint(Node)
    paged_tasks = Entrypoint(Connection(TaskType))

    @Entrypoint
    def function(self, arg: str = "None") -> list[str]:
        """
        Function docstring.

        :param arg: Argument docstring.
        """
        return [arg]


class Mutation(RootOperationType):
    create_task = Entrypoint(TaskCreateMutationType)

    bulk_create_task = Entrypoint(TaskCreateMutationType, many=True)


schema = create_schema(query=Query, mutation=Mutation)
