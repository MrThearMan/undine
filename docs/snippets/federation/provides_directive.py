from undine import Field, QueryType
from undine.federation import KeyDirective, ProvidesDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    project = Field() @ ProvidesDirective(fields="name")
