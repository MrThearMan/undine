"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:12: error: Directive "TestDirective" does not support location "INTERFACE"  [misc]
"""

from graphql import DirectiveLocation

from undine import InterfaceField
from undine.directives import Directive
from undine.interface import InterfaceType


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


@TestDirective()
class NamedObject(InterfaceType, schema_name="Named"):
    name = InterfaceField(str)
