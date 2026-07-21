"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from undine import Directive, InterfaceField, InterfaceType
from undine.typing import GQLInfo


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class Named(InterfaceType):
    name = InterfaceField(str) @ TestDirective()

    @TestDirective()
    @InterfaceField
    def foo(self, info: GQLInfo) -> int:
        return 0
