"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:13: error: Directive "TestDirective" does not support location "INPUT_FIELD_DEFINITION"  [misc]
main:15: error: Directive "TestDirective" does not support location "INPUT_FIELD_DEFINITION"  [misc]
"""

from django.db.models import Q
from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Directive, Filter, FilterSet, GQLInfo


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class TaskFilterSet(FilterSet[Task]):
    name = Filter() @ TestDirective()

    @TestDirective()
    @Filter
    def foo(self, info: GQLInfo, *, value: str) -> Q:
        return Q(name__icontains=value)
