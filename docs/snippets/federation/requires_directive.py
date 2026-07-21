from undine import Field, QueryType
from undine.federation import ExternalDirective, KeyDirective, RequiresDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field() @ ExternalDirective()
    display_name = Field() @ RequiresDirective(fields="name")
