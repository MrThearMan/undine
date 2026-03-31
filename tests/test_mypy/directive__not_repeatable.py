"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:12: error: Directive "MockDirective" is not repeatable  [misc]
main:13: error: Directive "MockDirective" is not repeatable  [misc]
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import QueryType
from undine.directives import Directive


class MockDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@MockDirective()
class TaskType(QueryType[Task], directives=[MockDirective()]): ...
