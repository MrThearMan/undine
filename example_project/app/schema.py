from __future__ import annotations

from example_project.app.mutations import TaskCreateMutation
from example_project.app.types import ReportNode, TaskNode
from undine import Entrypoint, create_schema


class Query:
    task = Entrypoint(TaskNode)
    tasks = Entrypoint(TaskNode, many=True)
    reports = Entrypoint(ReportNode, many=True)

    @Entrypoint
    def function(self, arg: str | None = None) -> list[str | None]:
        """
        Function docstring.

        :param arg: Argument docstring.
        """
        return [arg]


class Mutation:
    create_task = Entrypoint(TaskCreateMutation)


schema = create_schema(query_class=Query, mutation_class=Mutation)
