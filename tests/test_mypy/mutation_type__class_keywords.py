"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:8: error: Argument "kind" to "TaskCreateMutation" has incompatible type; expected "Literal['create', 'update', 'delete', 'related', 'custom']"  [arg-type]
main:9: error: Argument "related_action" to "TaskCreateMutation" has incompatible type; expected "Literal['null', 'delete', 'ignore']"  [arg-type]
main:10: error: Argument "auto" to "TaskCreateMutation" has incompatible type; expected "bool"  [arg-type]
main:11: error: Argument "exclude" to "TaskCreateMutation" has incompatible type; expected "list[str]"  [arg-type]
main:12: error: Argument "schema_name" to "TaskCreateMutation" has incompatible type; expected "str"  [arg-type]
main:13: error: Argument "directives" to "TaskCreateMutation" has incompatible type; expected "list[Directive]"  [arg-type]
main:14: error: Argument "extensions" to "TaskCreateMutation" has incompatible type; expected "dict[str, Any]"  [arg-type]
main:15: error: Unexpected keyword argument "typo_keyword" for "MutationType" class definition  [misc]
"""

from example_project.app.models import Task
from undine.mutation import MutationType


class TaskCreateMutation(
    MutationType[Task],
    kind="1",
    related_action="2",
    auto="3",
    exclude="4",
    schema_name=5,
    directives="6",
    extensions="7",
    typo_keyword=None,
): ...
