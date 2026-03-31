"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:10: error: Class "A" does not support directives  [misc]
"""

from graphql import DirectiveLocation

from undine.directives import Directive


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@TestDirective()
class A: ...
