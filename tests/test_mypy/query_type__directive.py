"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from example_project.app.models import Task
from undine.directives import Directive, DirectiveLocation
from undine.query import Field, QueryType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@TestDirective()
class TaskType(QueryType[Task]):
    name = Field()
