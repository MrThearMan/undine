"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:17: error: Directive "TestDirective" does not support location "UNION"  [misc]
"""

from graphql import DirectiveLocation

from example_project.app.models import Project, Task
from undine import Directive, QueryType, UnionType


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


@TestDirective()
class NamedUnion(UnionType[TaskType, ProjectType]): ...
