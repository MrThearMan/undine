"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:8: error: Argument "filterset" to "TaskType" has incompatible type; expected "type[FilterSet]"  [arg-type]
main:9: error: Argument "orderset" to "TaskType" has incompatible type; expected "type[OrderSet]"  [arg-type]
main:10: error: Argument "auto" to "TaskType" has incompatible type; expected "bool"  [arg-type]
main:11: error: Argument "exclude" to "TaskType" has incompatible type; expected "list[str]"  [arg-type]
main:12: error: Argument "cache_time" to "TaskType" has incompatible type; expected "int | None"  [arg-type]
main:13: error: Argument "cache_per_user" to "TaskType" has incompatible type; expected "bool"  [arg-type]
main:14: error: Argument "interfaces" to "TaskType" has incompatible type; expected "list[type[InterfaceType]]"  [arg-type]
main:15: error: Argument "register" to "TaskType" has incompatible type; expected "bool"  [arg-type]
main:16: error: Argument "schema_name" to "TaskType" has incompatible type; expected "str"  [arg-type]
main:17: error: Argument "directives" to "TaskType" has incompatible type; expected "list[Directive]"  [arg-type]
main:18: error: Argument "extensions" to "TaskType" has incompatible type; expected "dict[str, Any]"  [arg-type]
main:19: error: Unexpected keyword argument "typo_keyword" for "QueryType" class definition  [misc]
"""

from example_project.app.models import Task
from undine.query import QueryType


class TaskType(
    QueryType[Task],
    filterset="1",
    orderset="2",
    auto="3",
    exclude="4",
    cache_time="5",
    cache_per_user="6",
    interfaces="7",
    register="8",
    schema_name=9,
    directives="10",
    extensions="11",
    typo_keyword=None,
): ...
