"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from example_project.app.models import Project, Task
from undine import Directive, FilterSet, InterfaceType, OrderSet


class MockInterface(InterfaceType): ...


class MockDirective(Directive, locations=[DirectiveLocation.INTERFACE]): ...


class NamedFilterSet(FilterSet[Task, Project]): ...


class NamedOrderSet(OrderSet[Task, Project]): ...


class NamedInterface(
    InterfaceType,
    interfaces=[MockInterface],
    filterset=NamedFilterSet,
    orderset=NamedOrderSet,
    cache_time=1,
    cache_per_user=True,
    schema_name="named",
    directives=[MockDirective()],
    extensions={"foo": "bar"},
): ...
