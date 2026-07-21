from undine import Field, GQLInfo, QueryType
from undine.federation import FederationField, FederationType, KeyDirective

from .models import Task


@KeyDirective(fields="id", resolvable=False)
class UserStub(FederationType, schema_name="User"):
    id = FederationField(int)


@KeyDirective(fields="id")
class TaskType(QueryType[Task]):
    id = Field()
    name = Field()
    assigned_to = Field(UserStub, nullable=True)

    @assigned_to.resolve
    def resolve_assigned_to(root: Task, info: GQLInfo) -> dict | None:
        if root.assigned_to_id is None:
            return None
        return {"id": root.assigned_to_id}
