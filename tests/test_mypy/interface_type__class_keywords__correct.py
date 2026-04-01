"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from undine import Directive, InterfaceType


class MockInterface(InterfaceType): ...


class MockDirective(Directive, locations=[DirectiveLocation.INTERFACE]): ...


class NamedInterface(
    InterfaceType,
    interfaces=[MockInterface],
    cache_time=1,
    cache_per_user=True,
    schema_name="named",
    directives=[MockDirective()],
    extensions={"foo": "bar"},
): ...
