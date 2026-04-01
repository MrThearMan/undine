"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:10: error: Directive "TestDirective" does not support location "INTERFACE"  [misc]
"""

from graphql import DirectiveLocation

from undine import Directive, InterfaceField, InterfaceType


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


@TestDirective()
class NamedObject(InterfaceType, schema_name="Named"):
    name = InterfaceField(str)
