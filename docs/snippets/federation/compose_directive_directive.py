from undine import Entrypoint, Field, QueryType, RootType
from undine.federation import ComposeDirectiveDirective, create_federation_schema

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()


class Query(RootType):
    task = Entrypoint(TaskType)


schema = create_federation_schema(
    query=Query,
    schema_definition_directives=[ComposeDirectiveDirective(name="@custom")],
)
