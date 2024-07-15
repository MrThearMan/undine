from __future__ import annotations

from typing import Any, NamedTuple, Sequence

from django.test.signals import setting_changed
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString
from settings_holder import SettingsHolder, reload_settings

__all__ = [
    "undine_settings",
]


SETTING_NAME: str = "UNDINE"


class DefaultSettings(NamedTuple):
    ADD_ERROR_LOCATION: bool = True
    """Whether to add the location information to GraphQL errors."""

    ADDITIONAL_VALIDATION_RULES: Sequence[str] = ()
    """Additional validation rules to use for validating the GraphQL schema."""

    CAMEL_CASE_SCHEMA_FIELDS: bool = True
    """Should names be converted from snake case to camel case for the GraphQL schema?"""

    DISABLE_ONLY_FIELDS_OPTIMIZATION: bool = False
    """Disable optimizing fetched fields with `queryset.only()`."""

    DOCSTRING_PARSER: str = "undine.parsers.parse_docstring.RSTDocstringParser"
    """The docstring parser to use."""

    ENTRYPOINT_EXTENSIONS_KEY: str = "undine_entrypoint"
    """The key used to store a Entrypoint in the field GraphQL extensions."""

    FIELD_EXTENSIONS_KEY: str = "undine_field"
    """The key used to store a Field in the field GraphQL extensions."""

    FILTER_EXTENSIONS_KEY: str = "undine_filter"
    """The key used to store a Filter in the argument GraphQL extensions."""

    FILTER_INPUT_EXTENSIONS_KEY: str = "undine_filter_input"
    """The key used to store a ModelGQLFilter in the argument GraphQL extensions."""

    FILTER_INPUT_TYPE_KEY: str = "filter"
    """The key used for the filter input type of a ModelGQLType."""

    INPUT_EXTENSIONS_KEY: str = "undine_input"
    """The key used to store a Input in the argument GraphQL extensions."""

    GRAPHIQL_ENABLED: bool = False
    """Is GraphiQL enabled?"""

    GRAPHIQL_VERSION: str = "3.2.3"
    """The version of GraphiQL to use."""

    MAX_ERRORS: int = 100
    """The maximum number of validation errors allowed in a GraphQL request before it is rejected."""

    MAX_TOKENS: int = None
    """Maximum number of tokens the GraphQL parser will parse before it rejects a request"""

    MIDDLEWARE: Sequence[str] = ()
    """Middleware to use for in the GraphQL execution."""

    MODEL_TYPE_EXTENSIONS_KEY: str = "undine_type"
    """The key used to store a ModelGQLType in the object type GraphQL extensions."""

    MUTATION_EXTENSIONS_KEY: str = "undine_mutation"
    """The key used to store a Input in the argument GraphQL extensions."""

    MUTATION_INPUT_EXTENSIONS_KEY: str = "undine_mutation_input"
    """The key used to store a ModelGQLMutation in the argument GraphQL extensions."""

    MUTATION_INPUT_KEY: str = "input"
    """Key used for the mutation input data argument in mutations."""

    OPTIMIZER_MAX_COMPLEXITY: int = 10
    """Default max number of 'select_related' and 'prefetch related' joins optimizer is allowed to optimize."""

    ORDER_BY_EXTENSIONS_KEY: str = "undine_order_by"
    """The key used to store a Ordering in the argument GraphQL extensions."""

    ORDERING_INPUT_TYPE_KEY: str = "orderBy"
    """The key used for the order by argument of a ModelGQLType."""

    PLUGIN_EXPLORER_VERSION: str = "3.0.2"
    """The version of the plugin explorer to use for GraphiQL."""

    PREFETCH_COUNT_KEY: str = "_optimizer_count"
    """Name used for annotating the prefetched queryset total count."""

    PREFETCH_PARTITION_INDEX: str = "_optimizer_partition_index"
    """Name used for aliasing the prefetched queryset partition index."""

    PREFETCH_SLICE_START: str = "_optimizer_slice_start"
    """Name used for aliasing the prefetched queryset slice start."""

    PREFETCH_SLICE_STOP: str = "_optimizer_slice_stop"
    """Name used for aliasing the prefetched queryset slice end."""

    REACT_VERSION: str = "18.3.1"
    """The version of React to use for GraphiQL."""

    RELAY_CONNECTION_MAX_LIMIT: int = 100
    """The maximum number of items to display in a Relay connection."""

    RESOLVER_ROOT_PARAM_NAME: str = "root"
    """The name of the root/parent parameter in resolvers."""

    ROOT_VALUE: Any = None
    """The root value for the GraphQL execution."""

    SCHEMA: str = "undine.settings.example_schema"
    """The schema to use for the GraphQL API."""

    USE_PK_FIELD_NAME: bool = True
    """Should we use pk as the field name for primary keys?"""

    VALIDATE_NAMES_REVERSABLE: bool = True
    """
    When converting names to camels case, should we validate that they can be converted back to snake case?
    This is required for the optimizer to work correctly.
    """


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()

IMPORT_STRINGS: set[str] = {
    "SCHEMA",
    "DOCSTRING_PARSER",
    "MIDDLEWARE",
    "ADDITIONAL_VALIDATION_RULES",
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
