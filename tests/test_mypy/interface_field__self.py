"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from undine import InterfaceField, InterfaceType
from undine.typing import DjangoRequestProtocol, GQLInfo


class Named(InterfaceType):
    @InterfaceField
    def foo(self, info: GQLInfo) -> str:
        return "foo"

    bar = InterfaceField(str)

    @bar.visible
    def bar_visible(self, request: DjangoRequestProtocol) -> bool:
        assert_type(self, InterfaceField)
        return True
