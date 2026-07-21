"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:9: error: OrderSet decorator must be applied to a QueryType or UnionType subclass  [misc]
"""

from example_project.app.models import Task
from undine import MutationType, OrderSet


class TaskOrderSet(OrderSet[Task]): ...


@TaskOrderSet
class TaskMutation(MutationType[Task]): ...
