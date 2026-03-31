"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:20: error: InterfaceTypes can only be applied to a QueryType or InterfaceType subclass  [misc]
"""

from example_project.app.models import Task
from undine import InterfaceField, MutationType, QueryType
from undine.interface import InterfaceType


class HasID(InterfaceType, schema_name="HasID"):
    id = InterfaceField(int)


@HasID
class NamedObject(InterfaceType, schema_name="Named"):
    name = InterfaceField(str)


@NamedObject
class TaskType(QueryType[Task]): ...


@NamedObject
class TaskMutationType(MutationType[Task]): ...
