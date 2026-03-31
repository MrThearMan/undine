"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from undine.directives import Directive


class TestDirective(
    Directive,
    locations=[DirectiveLocation.QUERY],
    is_repeatable=False,
    schema_name="test",
    extensions={"foo": "bar"},
): ...
