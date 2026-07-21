"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from undine import InterfaceField, InterfaceType
from undine.typing import GQLInfo


class Named(InterfaceType):
    @InterfaceField
    def a(self, info: GQLInfo) -> int:
        """Regular method field"""
        return 0

    @InterfaceField
    def b(self) -> int:
        """Regular method field without info"""
        return 0

    @InterfaceField
    def c(self, info: GQLInfo, arg: int) -> int:
        """Regular method field with argument"""
        return 0

    @InterfaceField
    async def d(self, info: GQLInfo) -> int:
        """Async method field"""
        return 0
