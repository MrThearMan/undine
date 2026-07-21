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
    subtitle = FederationField(str, nullable=True)

    @subtitle.resolve
    def resolve_subtitle(self, info: GQLInfo) -> str | None:
        assert_type(self.subtitle, str | None)
        return self.subtitle
