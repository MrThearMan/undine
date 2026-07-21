from undine import Field, QueryType
from undine.federation import InterfaceObjectDirective, KeyDirective

from .models import Task


@InterfaceObjectDirective()
@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
