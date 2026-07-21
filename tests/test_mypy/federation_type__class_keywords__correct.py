"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from undine.federation import FederationField, FederationType, KeyDirective


@KeyDirective(fields="isbn")
class BookExtension(
    FederationType,
    schema_name="Book",
    extensions={"foo": "bar"},
):
    isbn = FederationField(str)
