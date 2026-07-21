"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:8: error: Argument "schema_name" to "BookExtension" has incompatible type; expected "str"  [arg-type]
main:9: error: Unexpected keyword argument "keys" for "FederationType" class definition  [misc]
"""

from undine.federation import FederationField, FederationType, KeyDirective


@KeyDirective(fields="isbn")
class BookExtension(
    FederationType,
    schema_name=1,
    keys="isbn",
):
    isbn = FederationField(str)
