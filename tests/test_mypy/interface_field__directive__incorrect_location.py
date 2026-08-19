"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:11: error: Directive "TestDirective" does not support location "FIELD_DEFINITION"  [misc]
"""

from graphql import DirectiveLocation

from undine import Directive, InterfaceField, InterfaceType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class Named(InterfaceType):
    name = InterfaceField(str) @ TestDirective()
