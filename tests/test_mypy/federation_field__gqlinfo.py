"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:11: error: Argument "info" has incompatible type "str"; expected 'undine.typing.GQLInfo'  [arg-type]
"""

from undine.federation import FederationField, FederationType, KeyDirective


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str)
    title = FederationField(str)

    @title.resolve
    def resolve_title(self, info: str) -> str:
        return "x"
