"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from undine.federation import FederationField, FederationType, KeyDirective


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str)
    reviews = FederationField(str, nullable=True)


BookExtension(isbn="x")
BookExtension(isbn="x", reviews="y")
BookExtension(isbn="x", reviews=None)
