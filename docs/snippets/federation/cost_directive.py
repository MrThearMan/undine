from undine import Field, QueryType
from undine.federation import CostDirective, KeyDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field() @ CostDirective(weight=5)
