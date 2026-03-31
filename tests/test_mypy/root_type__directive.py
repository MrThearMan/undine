"""
### mypy_config
[mypy]
plugins = mypy_undine
"""


from graphql import DirectiveLocation

from undine.directives import Directive
from undine.entrypoint import Entrypoint, RootType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@TestDirective()
class Query(RootType):
    @Entrypoint
    def foo(self) -> int:
        return 0
