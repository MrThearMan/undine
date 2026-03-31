"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""


from example_project.app.models import Task
from undine import Input, MutationType
from undine.directives import Directive, DirectiveLocation


class TestDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT]): ...


@TestDirective()
class TaskCreateMutation(MutationType[Task]):
    name = Input()
