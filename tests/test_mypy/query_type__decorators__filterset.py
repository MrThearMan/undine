"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:10: error: FilterSet model does not match QueryType model  [misc]
"""

from example_project.app.models import Person, Task
from undine.filtering import FilterSet
from undine.query import QueryType


class PersonFilterSet(FilterSet[Person]): ...


@PersonFilterSet
class TaskType(QueryType[Task]): ...
