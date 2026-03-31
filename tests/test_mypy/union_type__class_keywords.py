"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:18: error: Argument "filterset" to "NamedUnion" has incompatible type; expected "type[FilterSet]"  [arg-type]
main:19: error: Argument "orderset" to "NamedUnion" has incompatible type; expected "type[OrderSet]"  [arg-type]
main:20: error: Argument "schema_name" to "NamedUnion" has incompatible type; expected "str"  [arg-type]
main:21: error: Argument "cache_time" to "NamedUnion" has incompatible type; expected "int | None"  [arg-type]
main:22: error: Argument "cache_per_user" to "NamedUnion" has incompatible type; expected "bool"  [arg-type]
main:23: error: Argument "directives" to "NamedUnion" has incompatible type; expected "list[Directive]"  [arg-type]
main:24: error: Argument "extensions" to "NamedUnion" has incompatible type; expected "dict[str, Any]"  [arg-type]
main:25: error: Unexpected keyword argument "typo_keyword" for "UnionType" class definition  [misc]
"""

from example_project.app.models import Person, Project, Task
from undine import UnionType
from undine.query import QueryType


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class PersonType(QueryType[Person]): ...


class NamedUnion(
    UnionType[TaskType, ProjectType, PersonType],
    filterset="1",
    orderset="2",
    schema_name=3,
    cache_time="4",
    cache_per_user="5",
    directives="6",
    extensions="7",
    typo_keyword=None,
): ...
