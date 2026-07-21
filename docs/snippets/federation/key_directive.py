from undine import Field, QueryType
from undine.federation import KeyDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field()
