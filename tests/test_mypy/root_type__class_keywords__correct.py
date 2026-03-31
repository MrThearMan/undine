"""
### mypy_config
[mypy]
plugins = mypy_undine
"""

from graphql import DirectiveLocation

from undine.directives import Directive
from undine.entrypoint import RootType


class MockDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class Query(
    RootType,
    schema_name="Query",
    directives=[MockDirective()],
    extensions={"foo": "bar"},
): ...
