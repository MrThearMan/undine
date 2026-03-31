"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:7: error: Argument "interfaces" to "NamedInterface" has incompatible type; expected "list[type[InterfaceType]]"  [arg-type]
main:8: error: Argument "cache_time" to "NamedInterface" has incompatible type; expected "int | None"  [arg-type]
main:9: error: Argument "cache_per_user" to "NamedInterface" has incompatible type; expected "bool"  [arg-type]
main:10: error: Argument "schema_name" to "NamedInterface" has incompatible type; expected "str"  [arg-type]
main:11: error: Argument "directives" to "NamedInterface" has incompatible type; expected "list[Directive]"  [arg-type]
main:12: error: Argument "extensions" to "NamedInterface" has incompatible type; expected "dict[str, Any]"  [arg-type]
main:13: error: Unexpected keyword argument "typo_keyword" for "InterfaceType" class definition  [misc]
"""

from undine.interface import InterfaceType


class NamedInterface(
    InterfaceType,
    interfaces="1",
    cache_time="2",
    cache_per_user="3",
    schema_name=4,
    directives="5",
    extensions="6",
    typo_keyword=None,
): ...
