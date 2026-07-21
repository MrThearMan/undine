from typing import Any

from undine import Field, GQLInfo, QueryType
from undine.federation import KeyDirective

from .models import Task


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field()

    @classmethod
    def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> Task | None:
        return Task.objects.filter(pk=representation["id"]).first()
