"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from undine import GQLInfo
from undine.entrypoint import Entrypoint, RootType


class Query(RootType):
    @Entrypoint
    def foo(self, info: GQLInfo) -> int:
        """Correct signature with info"""
        return 0

    @Entrypoint
    def bar(self) -> int:
        """Correct signature without info"""
        return 0

    @Entrypoint
    def baz(self, info: GQLInfo, name: str) -> int:
        """Correct signature with info and argument"""
        return 0

    @Entrypoint
    def bax(self, name: str) -> int:
        """Correct signature without info and but with argument"""
        return 0
