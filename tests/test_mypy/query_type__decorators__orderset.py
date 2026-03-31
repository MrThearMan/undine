"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:10: error: OrderSet model does not match QueryType model  [misc]
"""

from example_project.app.models import Person, Task
from undine import OrderSet
from undine.query import QueryType


class PersonOrderSet(OrderSet[Person]): ...


@PersonOrderSet
class TaskType(QueryType[Task]): ...
