from undine import Field, QueryType
from undine.federation import KeyDirective, RequiresScopesDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field() @ RequiresScopesDirective(scopes=[["read:task"]])
