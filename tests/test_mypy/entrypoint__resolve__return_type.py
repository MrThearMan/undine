"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:12: error: Return type of resolver for "one" is incompatible with the Entrypoint ref type; expected a subtype of the ref type  [misc]
main:15: error: Return type of resolver for "many_ints" is incompatible with the Entrypoint ref type; expected a subtype of the ref type  [misc]
"""

from undine import GQLInfo
from undine.entrypoint import Entrypoint, RootType


class Query(RootType):
    one = Entrypoint(str)
    many_ints = Entrypoint(int, many=True)
    maybe = Entrypoint(str, nullable=True)

    @one.resolve
    def resolve_one(self, info: GQLInfo) -> int: ...

    @many_ints.resolve
    def resolve_many_ints(self, info: GQLInfo) -> int: ...

    @maybe.resolve
    def resolve_maybe(self, info: GQLInfo) -> str: ...
