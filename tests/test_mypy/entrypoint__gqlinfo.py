"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:7: error: Argument "info" has incompatible type "str"; expected 'undine.typing.GQLInfo'  [arg-type]
main:13: error: Argument "info" has incompatible type "str"; expected 'undine.typing.GQLInfo'  [arg-type]
"""

from undine.entrypoint import Entrypoint, RootType


class Query(RootType):
    @Entrypoint
    def foo(self, info: str) -> str:
        return "foo"

    bar = Entrypoint(str)

    @bar.resolve
    def resolve_bar(self, info: str) -> str:
        return "bar"
