"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:13: error: Argument 1 to "permissions" of "Entrypoint" has incompatible type "Callable[[Query], None]"; expected "Callable[[Any, GQLInfo[Any], Any], Awaitable[None] | None] | None"  [arg-type]
main:14: error: The @bad.permissions decorator must be applied to a method with signature 'def (self, info: GQLInfo, value: Any) -> None'  [misc]
"""

from undine import Entrypoint, GQLInfo, RootType


class Query(RootType):
    good = Entrypoint(str)

    @good.permissions
    def good_permissions(self, info: GQLInfo, value: str) -> None: ...

    bad = Entrypoint(str)

    @bad.permissions
    def bad_permissions(self) -> None: ...
