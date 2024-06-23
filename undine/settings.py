from __future__ import annotations

from typing import Any, NamedTuple

from django.test.signals import setting_changed
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString
from settings_holder import SettingsHolder, reload_settings

__all__ = [
    "undine_settings",
]


SETTING_NAME: str = "UNDINE"


class DefaultSettings(NamedTuple):
    SCHEMA: str = "undine.settings.example_schema"
    GRAPHIQL_ENABLED: bool = False
    GRAPHIQL_VERSION: str = "3.2.3"
    REACT_VERSION: str = "18.3.1"
    PLUGIN_EXPLORER_VERSION: str = "3.0.2"
    DOCSTRING_FORMAT: str = "reStructuredText"
    CURRENT_MODEL_KEY: str = "__current_node_model__"
    USE_PK_FIELD_NAME: bool = True
    CAMEL_CASE_SCHEMA_FIELDS: bool = True


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()

IMPORT_STRINGS: set[str] = {
    "SCHEMA",
}

undine_settings = SettingsHolder(
    setting_name=SETTING_NAME,
    defaults=DEFAULTS,
    import_strings=IMPORT_STRINGS,
)

reload_my_settings = reload_settings(SETTING_NAME, undine_settings)
setting_changed.connect(reload_my_settings)


# Placeholder schema
example_schema = GraphQLSchema(
    query=GraphQLObjectType(
        "Query",
        fields={
            "hello": GraphQLField(
                GraphQLString,
                resolve=lambda obj, info: "Hello, World!",  # noqa: ARG005
            )
        },
    ),
)
