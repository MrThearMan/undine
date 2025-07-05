from undine import Entrypoint, QueryType, RootType, create_schema

from .models import Task


class TaskType(QueryType[Task]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


schema = create_schema(query=Query)
