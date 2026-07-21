"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import Any, assert_type

from graphql import DirectiveLocation

from undine import Directive, DirectiveArgument


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]):
    one = DirectiveArgument(str)
    two = DirectiveArgument(str | None)

    def __connected__(self, other: Any) -> None:
        assert_type(self.one, str)
        assert_type(self.two, str | None)
