"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from graphql import DirectiveLocation

from undine import Directive
from undine.federation import FederationField, FederationType, KeyDirective


class MockDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str) @ MockDirective()
