"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:10: error: Argument "isbn" to "BookExtension" has incompatible type "int"; expected "str"  [arg-type]
"""

from undine.federation import FederationField, FederationType, KeyDirective


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str)


BookExtension(isbn=123)
