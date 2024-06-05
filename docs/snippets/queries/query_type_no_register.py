from undine import QueryType

from .models import Task


class TaskType(QueryType[Task]): ...


class OtherTaskType(QueryType[Task], register=False): ...
