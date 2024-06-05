from django.db.models import OuterRef

from undine import Field, QueryType
from undine.utils.model_utils import SubqueryCount

from .models import Task


class TaskType(QueryType[Task]):
    copies = Field(SubqueryCount(Task.objects.filter(name=OuterRef("name"))))
