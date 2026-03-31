"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:10: error: Argument "info" has incompatible type "str"; expected 'undine.typing.GQLInfo'  [arg-type]
"""

from django.db.models import Q

from example_project.app.models import Task
from undine import Filter, FilterSet


class TaskFilterSet(FilterSet[Task]):
    @Filter
    def name(self, info: str, *, value: str) -> Q:
        return Q(name__icontains=value)
