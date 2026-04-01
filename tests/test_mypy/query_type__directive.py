"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import Directive, Field, QueryType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@TestDirective()
class TaskType(QueryType[Task]):
    name = Field()
