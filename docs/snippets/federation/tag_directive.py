from undine import Field, QueryType
from undine.federation import KeyDirective, TagDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field() @ TagDirective(name="public") @ TagDirective(name="v2")
