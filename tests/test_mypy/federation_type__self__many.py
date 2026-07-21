"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from example_project.app.models import Task
from undine import QueryType
from undine.federation import FederationField, FederationType, KeyDirective
from undine.typing import GQLInfo


class TaskType(QueryType[Task]): ...


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str)
    tasks = FederationField(TaskType, many=True)

    @tasks.resolve
    def resolve_tasks(self, info: GQLInfo) -> list[Task]:
        assert_type(self.tasks, list[Task])
        return list(Task.objects.all())
