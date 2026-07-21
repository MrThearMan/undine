from undine import Field, QueryType
from undine.federation import KeyDirective, ListSizeDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    comments = Field() @ ListSizeDirective(
        assumed_size=100,
        slicing_arguments=["first", "last"],
        sized_fields=["edges"],
    )
