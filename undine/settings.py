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
    """The schema to use for the GraphQL API."""

    GRAPHIQL_ENABLED: bool = False
    """Is GraphiQL enabled?"""

    GRAPHIQL_VERSION: str = "3.2.3"
    """The version of GraphiQL to use."""

    REACT_VERSION: str = "18.3.1"
    """The version of React to use for GraphiQL."""

    PLUGIN_EXPLORER_VERSION: str = "3.0.2"
    """The version of the plugin explorer to use for GraphiQL."""

    DOCSTRING_PARSER: str = "undine.parsers.parse_docstring.RSTDocstringParser"
    """The docstring parser to use."""

    USE_PK_FIELD_NAME: bool = True
    """Should we use pk as the field name for primary keys?"""

    CAMEL_CASE_SCHEMA_FIELDS: bool = True
    """Should names be converted from snake case to camel case for the GraphQL schema?"""

    VALIDATE_NAMES_REVERSABLE: bool = True
    """
    When converting names to camels case, should we validate that they can be converted back to snake case?
    This is required for the optimizer to work correctly.
    """

    RESOLVER_ROOT_PARAM_NAME: str = "root"
    """The name of the root/parent parameter in resolvers."""

    RELAY_CONNECTION_MAX_LIMIT: int = 100
    """The maximum number of items to display in a Relay connection."""

    MODEL_TYPE_EXTENSIONS_KEY: str = "undine_type"
    """The key used to store a ModelGQLType in the object type GraphQL extensions."""

    FIELD_EXTENSIONS_KEY: str = "undine_field"
    """The key used to store a Field in the field GraphQL extensions."""

    FILTER_EXTENSIONS_KEY: str = "undine_filter"
    """The key used to store a Filter in the argument GraphQL extensions."""

    OPTIMIZER_MAX_COMPLEXITY: int = 10
    """Default max number of 'select_related' and 'prefetch related' joins optimizer is allowed to optimize."""

    DISABLE_ONLY_FIELDS_OPTIMIZATION: bool = False
    """Disable optimizing fetched fields with `queryset.only()`."""

    PREFETCH_COUNT_KEY: str = "_optimizer_count"
    """Name used for annotating the prefetched queryset total count."""

    PREFETCH_SLICE_START: str = "_optimizer_slice_start"
    """Name used for aliasing the prefetched queryset slice start."""

    PREFETCH_SLICE_STOP: str = "_optimizer_slice_stop"
    """Name used for aliasing the prefetched queryset slice end."""

    PREFETCH_PARTITION_INDEX: str = "_optimizer_partition_index"
    """Name used for aliasing the prefetched queryset partition index."""


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()

IMPORT_STRINGS: set[str] = {
    "SCHEMA",
    "DOCSTRING_PARSER",
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
