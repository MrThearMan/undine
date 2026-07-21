"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import assert_type

from undine.federation import FederationField, FederationType, KeyDirective
from undine.typing import GQLInfo


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str)
    title = FederationField(str)

    @title.resolve
    def resolve_title(self, info: GQLInfo) -> str:
        assert_type(self, BookExtension)
        assert_type(self.isbn, str)
        return f"Title of {self.isbn}"
