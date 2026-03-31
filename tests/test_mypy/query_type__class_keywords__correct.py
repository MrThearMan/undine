"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from example_project.app.models import Task
from undine import FilterSet, InterfaceType, OrderSet
from undine.directives import Directive
from undine.query import QueryType


class TaskFilterSet(FilterSet[Task]): ...


class TaskOrderSet(OrderSet[Task]): ...


class MockInterface(InterfaceType): ...


class MockDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class TaskType(
    QueryType[Task],
    filterset=TaskFilterSet,
    orderset=TaskOrderSet,
    auto=True,
    exclude=["foo", "bar"],
    cache_time=1,
    cache_per_user=True,
    interfaces=[MockInterface],
    register=True,
    schema_name="TaskQuery",
    directives=[MockDirective()],
    extensions={"foo": "bar"},
): ...
