"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:14: error: Return type of resolver for "title" is incompatible with the FederationField ref type; expected a subtype of the ref type  [misc]
main:17: error: Return type of resolver for "tags" is incompatible with the FederationField ref type; expected a subtype of the ref type  [misc]
"""

from undine.federation import FederationField, FederationType, KeyDirective
from undine.typing import GQLInfo


@KeyDirective(fields="isbn")
class BookExtension(FederationType, schema_name="Book"):
    isbn = FederationField(str)
    title = FederationField(str)
    tags = FederationField(str, many=True)
    subtitle = FederationField(str, nullable=True)

    @title.resolve
    def resolve_title(self, info: GQLInfo) -> int: ...

    @tags.resolve
    def resolve_tags(self, info: GQLInfo) -> str: ...

    @subtitle.resolve
    def resolve_subtitle(self, info: GQLInfo) -> str: ...
