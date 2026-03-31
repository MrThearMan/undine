"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:14: error: Missing named argument "one" for "TestDirective"  [call-arg]
main:14: error: Missing named argument "three" for "TestDirective"  [call-arg]
main:14: error: Argument "two" to "TestDirective" has incompatible type "int"; expected "str"  [arg-type]
"""

from example_project.app import models
from undine.directives import Directive, DirectiveArgument, DirectiveLocation
from undine.query import QueryType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]):
    one = DirectiveArgument(str)
    two = DirectiveArgument(str)
    three = DirectiveArgument(str | None)
    four = DirectiveArgument(str, default_value="foo")


@TestDirective(two=1)
class TaskType(QueryType[models.Task]): ...
