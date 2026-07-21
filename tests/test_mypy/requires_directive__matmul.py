"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:6: error: Directive "RequiresDirective" does not support location "OBJECT"  [misc]
"""

from undine.federation import FederationField, FederationType, KeyDirective, RequiresDirective


@KeyDirective(fields="isbn")
@RequiresDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str) @ RequiresDirective(fields="other")
