"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from example_project.app.models import Person, Project, Task
from undine import Directive, FilterSet, OrderSet, QueryType, UnionType


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class PersonType(QueryType[Person]): ...


class MockDirective(Directive, locations=[DirectiveLocation.UNION]): ...


class NamedFilterSet(FilterSet[Task, Project, Person]): ...


class NamedOrderSet(OrderSet[Task, Project, Person]): ...


class NamedUnion(
    UnionType[TaskType, ProjectType, PersonType],
    filterset=NamedFilterSet,
    orderset=NamedOrderSet,
    schema_name="named",
    cache_time=1,
    cache_per_user=True,
    directives=[MockDirective()],
    extensions={"foo": "bar"},
): ...
