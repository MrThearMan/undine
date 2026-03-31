"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:19: error: OrderSet models do not match UnionType member models  [misc]
"""

from example_project.app.models import Person, Project, Task
from undine import OrderSet, UnionType
from undine.query import QueryType


class PersonOrderSet(OrderSet[Task, Person]): ...


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class PersonType(QueryType[Person]): ...


@PersonOrderSet
class NamedUnion(UnionType[TaskType, ProjectType, PersonType]): ...
