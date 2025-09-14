from undine import Entrypoint, Field, QueryType, RootType, create_schema

from .models import Project, Step, Task


class ProjectType(QueryType[Project]):
    pk = Field()
    name = Field()
    tasks = Field()


class TaskType(QueryType[Task]):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()
    project = Field()
    steps = Field()


class StepType(QueryType[Step]):
    pk = Field()
    name = Field()
    done = Field()
    task = Field()


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


schema = create_schema(query=Query)
