"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from undine.federation import ExternalDirective, FederationField, FederationType, KeyDirective


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str)
    weight = FederationField(int) @ ExternalDirective()


BookExtension(isbn="x")
BookExtension(isbn="x", weight=1)
BookExtension(isbn="x", weight=None)
