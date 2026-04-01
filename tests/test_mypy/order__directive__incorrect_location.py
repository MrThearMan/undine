"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:12: error: Directive "TestDirective" does not support location "ENUM_VALUE"  [misc]
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Directive, Order, OrderSet


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class TaskOrderSet(OrderSet[Task]):
    name = Order() @ TestDirective()
