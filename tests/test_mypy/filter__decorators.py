"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:15: error: Argument "value" to must be a keyword-only argument  [misc]
main:20: error: The third argument to "baz" must be named "value"  [misc]
main:25: error: Return type of bax has incompatible type "str"; expected 'django.db.models.query_utils.Q'  [misc]
"""

from django.db.models import Q

from example_project.app.models import Task
from undine import Filter, FilterSet, GQLInfo


class TaskFilterSet(FilterSet[Task]):
    @Filter
    def foo(self, info: GQLInfo, *, value: str) -> Q:
        """Correct signature"""
        return Q(name__icontains=value)

    @Filter
    def bar(self, info: GQLInfo, value: str) -> Q:
        """Incorrect signature: value not a keyword argument"""
        return Q(name__icontains=value)

    @Filter
    def baz(self, info: GQLInfo, *, name: str) -> Q:
        """Incorrect signature: keyword argument not named 'value'"""
        return Q(name__icontains=name)

    @Filter
    def bax(self, info: GQLInfo, *, value: str) -> str:
        """Incorrect signature: doesn't return Q"""
        return "foo"
