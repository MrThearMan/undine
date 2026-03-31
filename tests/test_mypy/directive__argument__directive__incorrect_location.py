"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:9: error: Directive "TestDirective" does not support location "ARGUMENT_DEFINITION"  [misc]
"""

from undine.directives import Directive, DirectiveArgument, DirectiveLocation


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class OtherDirective(Directive, locations=[DirectiveLocation.OBJECT]):
    one = DirectiveArgument(str) @ TestDirective()
