from undine import GQLInfo
from undine.federation import ExternalDirective, FederationField, FederationType, KeyDirective, RequiresDirective

from .models import Task


@KeyDirective(fields="id")
class UserExtension(FederationType, schema_name="User"):
    id = FederationField(int)

    # Populated by the Users subgraph.
    timezone = FederationField(str) @ ExternalDirective()

    # "Overdue" depends on the user's local time, so we need `timezone` resolved first.
    overdue_task_count = FederationField(int) @ RequiresDirective(fields="timezone")

    @overdue_task_count.resolve
    def resolve_overdue_task_count(self, info: GQLInfo) -> int:
        return Task.objects.filter(assigned_to_id=self.id, due_by__lt=self.timezone).count()
