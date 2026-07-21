from undine import Field, QueryType
from undine.federation import ContextDirective, KeyDirective

from .models import Task


@ContextDirective(name="workspace")
@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
