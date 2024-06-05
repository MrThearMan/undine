from undine import Entrypoint, FilterSet, QueryType, RootType, create_schema

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskFilterSet(FilterSet[Task]): ...


class TaskType(QueryType[Task], filterset=TaskFilterSet): ...


class StepType(QueryType[Step]): ...


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True)


schema = create_schema(query=Query)
