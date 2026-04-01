"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from django.db.models import Q, Value

from example_project.app.models import Task
from undine import Filter, FilterSet, GQLInfo
from undine.typing import DjangoExpression, DjangoRequestProtocol


class TaskFilterSet(FilterSet[Task]):
    @Filter
    def foo(self, info: GQLInfo, *, value: str) -> Q:
        assert_type(self, Filter)
        return Q(name__icontains=value)

    @foo.aliases
    def foo_aliases(self, info: GQLInfo, *, value: str) -> dict[str, DjangoExpression]:
        assert_type(self, Filter)
        return {"foo": Value("bar")}

    @foo.visible
    def foo_visible(self, request: DjangoRequestProtocol) -> bool:
        assert_type(self, Filter)
        return True
