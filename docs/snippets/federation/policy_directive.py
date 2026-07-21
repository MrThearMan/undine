from undine import Field, QueryType
from undine.federation import KeyDirective, PolicyDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field() @ PolicyDirective(policies=[["policy_a"], ["policy_b"]])
