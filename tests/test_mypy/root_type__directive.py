"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from undine import Directive, Entrypoint, RootType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@TestDirective()
class Query(RootType):
    @Entrypoint
    def foo(self) -> int:
        return 0
