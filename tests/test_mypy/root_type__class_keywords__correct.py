"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from undine import Directive, RootType


class MockDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class Query(
    RootType,
    schema_name="Query",
    directives=[MockDirective()],
    extensions={"foo": "bar"},
): ...
