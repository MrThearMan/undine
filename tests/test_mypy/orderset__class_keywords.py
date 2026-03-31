"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:8: error: Argument "auto" to "TaskOrderSet" has incompatible type; expected "bool"  [arg-type]
main:9: error: Argument "exclude" to "TaskOrderSet" has incompatible type; expected "list[str]"  [arg-type]
main:10: error: Argument "schema_name" to "TaskOrderSet" has incompatible type; expected "str"  [arg-type]
main:11: error: Argument "directives" to "TaskOrderSet" has incompatible type; expected "list[Directive]"  [arg-type]
main:12: error: Argument "extensions" to "TaskOrderSet" has incompatible type; expected "dict[str, Any]"  [arg-type]
main:13: error: Unexpected keyword argument "typo_keyword" for "OrderSet" class definition  [misc]
"""

from example_project.app.models import Task
from undine.ordering import OrderSet


class TaskOrderSet(
    OrderSet[Task],
    auto="1",
    exclude="2",
    schema_name=3,
    directives="4",
    extensions="5",
    typo_keyword=None,
): ...
