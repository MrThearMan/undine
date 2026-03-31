"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:10: error: Directive "TestDirective" does not support location "INPUT_OBJECT"  [misc]
"""

from example_project.app.models import Task
from undine import Input, MutationType
from undine.directives import Directive, DirectiveLocation


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


@TestDirective()
class TaskCreateMutation(MutationType[Task]):
    name = Input()
