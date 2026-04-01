"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from graphql import DirectiveLocation

from undine import Directive, DirectiveArgument


class TestDirective(Directive, locations=[DirectiveLocation.ARGUMENT_DEFINITION]): ...


class OtherDirective(Directive, locations=[DirectiveLocation.OBJECT]):
    one = DirectiveArgument(str) @ TestDirective()


assert_type(OtherDirective.one, DirectiveArgument)
