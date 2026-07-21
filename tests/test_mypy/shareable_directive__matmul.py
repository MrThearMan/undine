"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from example_project.app.models import Task
from undine import QueryType
from undine.federation import FederationField, FederationType, KeyDirective, ShareableDirective


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str) @ ShareableDirective()


@ShareableDirective()
class TaskType(QueryType[Task]): ...
