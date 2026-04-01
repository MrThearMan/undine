"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:7: error: Argument "schema_name" to "Query" has incompatible type; expected "str"  [arg-type]
main:8: error: Argument "directives" to "Query" has incompatible type; expected "list[Directive]"  [arg-type]
main:9: error: Argument "extensions" to "Query" has incompatible type; expected "dict[str, Any]"  [arg-type]
main:10: error: Unexpected keyword argument "typo_keyword" for "RootType" class definition  [misc]
"""

from undine.entrypoint import RootType


class Query(
    RootType,
    schema_name=1,
    directives="2",
    extensions="3",
    typo_keyword=None,
): ...
