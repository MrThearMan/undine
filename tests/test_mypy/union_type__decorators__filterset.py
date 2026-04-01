"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:18: error: FilterSet models do not match UnionType member models  [misc]
"""

from example_project.app.models import Person, Project, Task
from undine import FilterSet, QueryType, UnionType


class PersonFilterSet(FilterSet[Task, Person]): ...


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class PersonType(QueryType[Person]): ...


@PersonFilterSet
class NamedUnion(UnionType[TaskType, ProjectType, PersonType]): ...
