"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:7: error: Argument "locations" to "TestDirective" has incompatible type; expected "list[DirectiveLocation]"  [arg-type]
main:8: error: Argument "is_repeatable" to "TestDirective" has incompatible type; expected "bool"  [arg-type]
main:9: error: Argument "schema_name" to "TestDirective" has incompatible type; expected "str"  [arg-type]
main:10: error: Argument "extensions" to "TestDirective" has incompatible type; expected "dict[str, Any]"  [arg-type]
main:11: error: Unexpected keyword argument "typo_keyword" for "Directive" class definition  [misc]
"""

from undine.directives import Directive


class TestDirective(
    Directive,
    locations="1",
    is_repeatable="2",
    schema_name=3,
    extensions="5",
    typo_keyword=None,
): ...
