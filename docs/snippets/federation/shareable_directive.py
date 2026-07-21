from undine import Field, QueryType
from undine.federation import ShareableDirective

from .models import Task


class TaskType(QueryType[Task]):
    id = Field()
    name = Field() @ ShareableDirective()
