"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from django.db.models import Q
from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Filter, FilterSet, GQLInfo
from undine.directives import Directive


class TestDirective(Directive, locations=[DirectiveLocation.INPUT_FIELD_DEFINITION]): ...


class TaskFilterSet(FilterSet[Task]):
    name = Filter() @ TestDirective()

    @TestDirective()
    @Filter
    def foo(self, info: GQLInfo, *, value: str) -> Q:
        return Q(name__icontains=value)
