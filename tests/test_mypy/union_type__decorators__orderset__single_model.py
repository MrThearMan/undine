"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:19: error: OrderSet used on UnionType must be parameterized with multiple models  [misc]
"""

from example_project.app.models import Person, Project, Task
from undine import OrderSet, UnionType
from undine.query import QueryType


class TaskOrderSet(OrderSet[Task]): ...


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class PersonType(QueryType[Person]): ...


@TaskOrderSet
class NamedUnion(UnionType[TaskType, ProjectType, PersonType]): ...
