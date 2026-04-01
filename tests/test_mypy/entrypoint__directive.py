"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from undine import Directive, Entrypoint, GQLInfo, RootType


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class Query(RootType):
    foo = Entrypoint() @ TestDirective()

    @foo.resolve
    def resolve_foo(self, info: GQLInfo) -> int:
        return 0

    @TestDirective()
    @Entrypoint
    def bar(self, info: GQLInfo) -> int:
        return 0
