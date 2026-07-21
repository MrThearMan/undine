from undine import Field, QueryType
from undine.federation import InaccessibleDirective, KeyDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    internal_note = Field() @ InaccessibleDirective()
