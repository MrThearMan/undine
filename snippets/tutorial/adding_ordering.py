from undine import Entrypoint, OrderSet, QueryType, RootType, create_schema

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskOrderSet(OrderSet[Task]): ...


class TaskType(QueryType[Task], orderset=TaskOrderSet): ...


class StepType(QueryType[Step]): ...


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True)


schema = create_schema(query=Query)
