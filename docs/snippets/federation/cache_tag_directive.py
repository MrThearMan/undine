from undine import Field, QueryType
from undine.federation import CacheTagDirective, KeyDirective

from .models import Task


@CacheTagDirective(format="task")
@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field() @ CacheTagDirective(format="task:{$response.id}:name")
