from undine import Field, Input, MutationType, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @classmethod
    def __query_type__(cls) -> type[QueryType]:
        return TaskType
