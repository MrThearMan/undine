from undine import Field, GQLInfo, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    @Field
    def greeting(self, info: GQLInfo) -> str:
        return "Hello World!"
