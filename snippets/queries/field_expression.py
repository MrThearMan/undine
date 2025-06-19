from django.db.models.functions import Upper

from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    upper_name = Field(Upper("name"))
