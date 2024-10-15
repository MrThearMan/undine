from __future__ import annotations

from example_project.app.mutations import TaskCreateMutationType
from example_project.app.types import ReportType, TaskType
from undine import Entrypoint, create_schema


class Query:
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)
    reports = Entrypoint(ReportType, many=True)

    @Entrypoint
    def function(self, arg: str = "None") -> list[str]:
        """
        Function docstring.

        :param arg: Argument docstring.
        """
        return [arg]


class Mutation:
    create_task = Entrypoint(TaskCreateMutationType)


schema = create_schema(query_class=Query, mutation_class=Mutation)
