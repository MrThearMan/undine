"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:11: error: Directive "TestDirective" does not support location "INPUT_OBJECT"  [misc]
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Directive, FilterSet


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@TestDirective()
class TaskFilterSet(FilterSet[Task]): ...
