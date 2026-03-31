"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:13: error: Directive "TestDirective" does not support location "FIELD_DEFINITION"  [misc]
main:19: error: Directive "TestDirective" does not support location "FIELD_DEFINITION"  [misc]
"""

from graphql import DirectiveLocation

from undine import GQLInfo
from undine.directives import Directive
from undine.entrypoint import Entrypoint, RootType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class Query(RootType):
    foo = Entrypoint() @ TestDirective()

    @foo.resolve
    def resolve_foo(self, info: GQLInfo) -> int:
        return 0

    @TestDirective()
    @Entrypoint
    def bar(self, info: GQLInfo) -> int:
        return 0
