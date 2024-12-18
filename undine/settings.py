"""Django settings for Undine. Can be configured in the Django settings file with the key 'UNDINE'."""

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
    ADDITIONAL_VALIDATION_RULES: list[str] = []
    """Additional validation rules to use for validating the GraphQL schema."""

    CAMEL_CASE_SCHEMA_FIELDS: bool = True
    """Should names be converted from snake case to camel case for the GraphQL schema?"""

    CONNECTION_EXTENSIONS_KEY: str = "undine_connection"
    """The key to use for storing the connection in the extensions of the GraphQL type."""

    CONNECTION_MAX_LIMIT: int = 100
    """The maximum number of items to return in a connection by default."""

    CONNECTION_START_INDEX_HINT_KEY = "undine_start_index"
    """The key to use for storing the start index of objects in a connection in the queryset hints."""

    CONNECTION_STOP_INDEX_HINT_KEY = "undine_stop_index"
    """The key to use for storing the stop index of objects in a connection in the queryset hints."""

    CONNECTION_TOTAL_COUNT_HINT_KEY = "undine_total_count"
    """The key to use for storing the total count of objects in a connection in the queryset hints."""

    DELETE_MUTATION_OUTPUT_FIELD_NAME: str = "success"
    """The name of the field in the output of a delete mutation."""

    DISABLE_ONLY_FIELDS_OPTIMIZATION: bool = False
    """Disable optimizing fetched fields with `queryset.only()`."""

    DOCSTRING_PARSER: str = "undine.parsers.parse_docstring.RSTDocstringParser"
    """The docstring parser to use."""

    ENTRYPOINT_EXTENSIONS_KEY: str = "undine_entrypoint"
    """The key used to store a Entrypoint in the field GraphQL extensions."""

    EXECUTION_CONTEXT_CLASS: str = "undine.schema.UndineExecutionContext"
    """GraphQL execution context class used by the schema."""

    FIELD_EXTENSIONS_KEY: str = "undine_field"
    """The key used to store a Field in the field GraphQL extensions."""

    FILTER_EXTENSIONS_KEY: str = "undine_filter"
    """The key used to store a Filter in the argument GraphQL extensions."""

    FILTER_INPUT_TYPE_KEY: str = "filter"
    """The key used for the filter input type of a QueryType."""

    FILTERSET_EXTENSIONS_KEY: str = "undine_filterset"
    """The key used to store a FilterSet in the argument GraphQL extensions."""

    INPUT_EXTENSIONS_KEY: str = "undine_input"
    """The key used to store a Input in the argument GraphQL extensions."""

    GRAPHIQL_ENABLED: bool = False
    """Is GraphiQL enabled?"""

    GRAPHIQL_VERSION: str = "3.2.3"
    """The version of GraphiQL to use."""

    LOOKUP_EXPRESSIONS_MANY: tuple[str, ...] = ("in", "range")
    """Lookup expressions that should be assumed to require a list of values."""

    MAX_ERRORS: int = 100
    """The maximum number of validation errors allowed in a GraphQL request before it is rejected."""

    MAX_TOKENS: int = None
    """Maximum number of tokens the GraphQL parser will parse before it rejects a request"""

    MIDDLEWARE: list[str] = []
    """Middleware to use in GraphQL field resolving."""

    MUTATION_EXTENSIONS_KEY: str = "undine_mutation"
    """The key used to store a Mutation in the argument GraphQL extensions."""

    MUTATION_INPUT_KEY: str = "input"
    """The key used for the input argument of a MutationType."""

    NO_ERROR_LOCATION: bool = False
    """Whether to add the location information to GraphQL errors."""

    OPTIMIZER_MAX_COMPLEXITY: int = 10
    """Default max number of 'select_related' and 'prefetch related' joins optimizer is allowed to optimize."""

    ORDER_EXTENSIONS_KEY: str = "undine_order"
    """The key used to store a Order in the argument GraphQL extensions."""

    ORDER_BY_INPUT_TYPE_KEY: str = "orderBy"
    """The key used for the order by argument of a QueryType."""

    ORDERSET_EXTENSIONS_KEY: str = "undine_orderset"
    """The key used to store a OrderSet in the argument GraphQL extensions."""

    PLUGIN_EXPLORER_VERSION: str = "3.0.2"
    """The version of the plugin explorer to use for GraphiQL."""

    QUERY_TYPE_EXTENSIONS_KEY: str = "undine_type"
    """The key used to store a QueryType in the object type GraphQL extensions."""

    REACT_VERSION: str = "18.3.1"
    """The version of React to use for GraphiQL."""

    RELAY_CONNECTION_MAX_LIMIT: int = 100
    """The maximum number of items to display in a Relay connection."""

    RELAY_CURSOR_PREFIX: str = "arrayconnection"
    """The prefix to use for Relay cursors."""

    RESOLVER_ROOT_PARAM_NAME: str = "root"
    """The name of the root/parent parameter in resolvers."""

    ROOT_VALUE: Any = None
    """The root value for the GraphQL execution."""

    SCHEMA: str = "undine.settings.example_schema"
    """The schema to use for the GraphQL API."""

    TESTING_ENDPOINT: str = "/graphql/"
    """The endpoint to use for testing."""

    USE_PK_FIELD_NAME: bool = True
    """Should we use pk as the field name for primary keys?"""

    VALIDATE_NAMES_REVERSIBLE: bool = True
    """
    When converting names to camels case, should we validate that they can be converted back to snake case?
    This is required for the optimizer to work correctly.
    """


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()

IMPORT_STRINGS: set[str] = {
    "ADDITIONAL_VALIDATION_RULES.0",
    "DOCSTRING_PARSER",
    "EXECUTION_CONTEXT_CLASS",
    "MIDDLEWARE.0",
    "MUTATION_MIDDLEWARE.0",
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
            ),
        },
    ),
)
