"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from undine import GQLInfo
from undine.entrypoint import Entrypoint, RootType


class Query(RootType):
    @Entrypoint
    def foo(self, info: GQLInfo) -> str:
        assert_type(self, None)
        return "foo"

    bar = Entrypoint(str)

    @bar.resolve
    def resolve_bar(self, info: GQLInfo) -> str:
        assert_type(self, None)
        return "bar"
