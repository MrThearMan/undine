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
    RESPONSE_CONTENT_TYPE: str = "application/graphql-response+json"


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
