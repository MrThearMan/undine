"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:11: error: Directive "TestDirective" does not support location "OBJECT"  [misc]
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Directive, QueryType


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


@TestDirective()
class TaskType(QueryType[Task]): ...
