"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""


from graphql import DirectiveLocation

from example_project.app.models import Project, Task
from undine import QueryType, UnionType
from undine.directives import Directive


class TestDirective(Directive, locations=[DirectiveLocation.UNION]): ...


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


@TestDirective()
class NamedUnion(UnionType[TaskType, ProjectType]): ...
