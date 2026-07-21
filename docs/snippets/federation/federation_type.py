from undine.federation import FederationField, FederationType, KeyDirective

from .models import Task


@KeyDirective(fields="id")
class UserExtension(FederationType, schema_name="User"):
    id = FederationField(int)
    assigned_task_count = FederationField(int)

    @assigned_task_count.resolve
    def resolve_assigned_task_count(self, info) -> int:
        # `self.id` reads from the representation the router sent.
        return Task.objects.filter(assigned_to_id=self.id).count()
