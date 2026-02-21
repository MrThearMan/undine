"""Django settings for Undine. Can be configured in the Django settings file with the key 'UNDINE'."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from django.test.signals import setting_changed
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString
from settings_holder import SettingsHolder, reload_settings

if TYPE_CHECKING:
    from collections.abc import Container

    from graphql import ASTValidationRule

    from undine.execution import UndineExecutionContext
    from undine.hooks import LifecycleHook
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.typing import (
        DocstringParserProtocol,
        PersistedDocumentsPermissionsCallback,
        WebSocketConnectionInitHook,
        WebSocketConnectionPingHook,
        WebSocketConnectionPongHook,
    )
    from undine.utils.graphql.sdl_printer import SDLPrinter


__all__ = [
    "undine_settings",
]


SETTING_NAME: str = "UNDINE"


class UndineDefaultSettings(NamedTuple):
    """Default settings for Undine."""

    # Schema

    SCHEMA: GraphQLSchema = "undine.settings.example_schema"  # type: ignore[assignment]
    """The schema to use for the GraphQL API."""

    GRAPHQL_PATH: str = "graphql/"
    """The path where the GraphQL endpoint is located by default."""

    GRAPHQL_VIEW_NAME: str = "graphql"
    """The name of given to the GraphQL view in the URLconf."""

    # Flags

    AUTOGENERATION: bool = False
    """Whether to automatically generate fields & inputs for some Undine types or not."""

    ALLOW_DID_YOU_MEAN_SUGGESTIONS: bool = False
    """Whether to allow the 'did you mean' suggestions on error messages."""

    ALLOW_INTROSPECTION_QUERIES: bool = False
    """Whether schema introspection queries are allowed or not."""

    ASYNC: bool = False
    """Whether to use an async view for the GraphQL endpoint or not."""

    CAMEL_CASE_SCHEMA_FIELDS: bool = True
    """Should names be converted from 'snake_case' to 'camelCase' for the GraphQL schema?"""

    ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS: bool = False
    """Whether to parse class attribute docstrings or not."""

    FILE_UPLOAD_ENABLED: bool = False
    """Whether file uploads are enabled. Should enable CSRF protection on the GraphiQL endpoint if enabled."""

    INCLUDE_ERROR_TRACEBACK: bool = False
    """Whether to include the error traceback in the response error extensions."""

    MUTATION_FULL_CLEAN: bool = True
    """Whether to run `model.full_clean()` when mutating a model."""

    EXPERIMENTAL_VISIBILITY_CHECKS: bool = False  # Experimental, may not work as expected
    """Whether to enable experimental visibility checks."""

    # Limits

    LIST_ENTRYPOINT_LIMIT: int | None = None
    """
    Maximum number of objects that can be returned from a list Entrypoint when not using pagination.
    If None, all items are fetched.
    """

    MAX_FILTERS_PER_TYPE: int = 20
    """The maximum number of filters allowed for a single `FilterSet`."""

    MAX_ORDERS_PER_TYPE: int = 10
    """The maximum number of orders allowed for a single `OrderSet`."""

    # Pagination

    PAGINATION_PAGE_SIZE: int | None = 100
    """The maximum number of items to return in a page when paginating."""

    PAGINATION_START_INDEX_KEY: str = "_undine_pagination_start"
    """The key to which the connection's pagination start index is annotated to or added to in the queryset hints."""

    PAGINATION_STOP_INDEX_KEY: str = "_undine_pagination_stop"
    """The key to which the connection's pagination stop index is annotated to or added to in the queryset hints."""

    PAGINATION_INDEX_KEY: str = "_undine_pagination_index"
    """The key to which nested connection node's pagination index is annotated to the queryset."""

    PAGINATION_TOTAL_COUNT_KEY: str = "_undine_pagination_total_count"
    """The key to which the connection's total count annotated to or added to in the queryset hints."""

    # GraphQL execution

    ADDITIONAL_VALIDATION_RULES: list[type[ASTValidationRule]] = []
    """Additional validation rules to use for validating the GraphQL schema."""

    EXECUTION_CONTEXT_CLASS: type[UndineExecutionContext] = "undine.execution.UndineExecutionContext"  # type: ignore[assignment]
    """GraphQL execution context class used by the schema."""

    LIFECYCLE_HOOKS: list[type[LifecycleHook]] = []
    """Lifecycle hooks to use during GraphQL operations."""

    MAX_ALLOWED_ALIASES: int = 15
    """The maximum number of aliases allowed in a single operation."""

    MAX_ALLOWED_DIRECTIVES: int = 50
    """The maximum number of directives allowed in a single operation."""

    MAX_ERRORS: int = 100
    """The maximum number of validation errors allowed in a GraphQL request before it is rejected."""

    MAX_QUERY_COMPLEXITY: int = 10
    """Maximum query complexity that is allowed to be queried in a single operation."""

    MAX_TOKENS: int | None = None
    """Maximum number of tokens the GraphQL parser will parse before it rejects a request"""

    MUTATION_INSTANCE_LIMIT: int = 100
    """The maximum number of objects that can be mutated in a single mutation."""

    NO_ERROR_LOCATION: bool = False
    """Whether to add the location information to GraphQL errors."""

    ROOT_VALUE: Any = None
    """The root value for the GraphQL execution."""

    # Testing client

    TESTING_CLIENT_FULL_STACKTRACE: bool = False
    """Whether to include the full stacktrace in testing client instead of just the relevant frames."""

    TESTING_CLIENT_NO_ASYNC_TIMEOUT: bool = False
    """Whether to disable the websocket timeouts in testing client."""

    # GraphiQL

    GRAPHIQL_ENABLED: bool = False
    """Is GraphiQL enabled?"""

    # Persisted documents

    PERSISTED_DOCUMENTS_ONLY: bool = False
    """Whether to only allow persisted documents to be executed."""

    PERSISTED_DOCUMENTS_PATH: str = "persisted-documents/"
    """The path where the persisted documents registration endpoint is located by default."""

    PERSISTED_DOCUMENTS_PERMISSION_CALLBACK: PersistedDocumentsPermissionsCallback = (
        "undine.persisted_documents.utils.default_permission_callback"  # type: ignore[assignment]
    )
    """The function to use for permission checks for registration of persisted documents."""

    PERSISTED_DOCUMENTS_VIEW_NAME: str = "persisted_documents"
    """The name of given to the persisted documents registration view in the URLconf."""

    # WebSocket

    ALLOW_QUERIES_WITH_WEBSOCKETS: bool = False
    """Whether queries can be executed over WebSockets."""

    ALLOW_MUTATIONS_WITH_WEBSOCKETS: bool = False
    """Whether mutations can be executed over WebSockets."""

    WEBSOCKET_CONNECTION_INIT_HOOK: WebSocketConnectionInitHook = "undine.utils.graphql.websocket.connection_init_hook"  # type: ignore[assignment]
    """The function to use for custom `ConnectionInit` logic."""

    WEBSOCKET_CONNECTION_INIT_TIMEOUT_SECONDS: int = 3
    """The number of seconds to wait for the `ConnectionInit` message after opening a WebSocket before closing it."""

    WEBSOCKET_PATH: str = "graphql/"
    """The path where the GraphQL over WebSocket endpoint is located."""

    WEBSOCKET_PING_HOOK: WebSocketConnectionPingHook = "undine.utils.graphql.websocket.ping_hook"  # type: ignore[assignment]
    """The function for specifying custom `Ping` message logic."""

    WEBSOCKET_PONG_HOOK: WebSocketConnectionPongHook = "undine.utils.graphql.websocket.pong_hook"  # type: ignore[assignment]
    """The function to for specifying custom `Pong` message logic."""

    # Server-Sent Events

    ALLOW_QUERIES_WITH_SSE: bool = False
    """Whether queries can be executed over Server-Sent Events."""

    ALLOW_MUTATIONS_WITH_SSE: bool = False
    """Whether mutations can be executed over Server-Sent Events."""

    SSE_STREAM_SESSION_PREFIX: str = "graphql-over-sse-stream"
    """Key prefix used to store the GraphQL over SSE stream state in the user's session (Single Connection mode)."""

    SSE_TOKEN_HEADER_NAME: str = "X-GraphQL-Event-Stream-Token"  # noqa: S105
    """The name of the HTTP header to use for the GraphQL over SSE event stream token (Single Connection mode)."""

    SSE_TOKEN_QUERY_PARAM_NAME: str = "token"  # noqa: S105
    """
    The name of the query string parameter to use for the
    GraphQL over SSE event stream token (Single Connection mode).
    """

    SSE_KEEP_ALIVE_INTERVAL: int = 12
    """Interval in seconds for SSE keep-alive pings. Set to 0 to disable."""

    SSE_OPERATION_STREAM_OPEN_TIMEOUT: int = 30
    """Timeout in seconds for an SSE operation to wait for the event stream to open (Single Connection mode)."""

    USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1: bool = False
    """Whether to allow SSE distinct connections mode over HTTP/1.1. Use only if you know what you're doing."""

    # Django-modeltranslation

    MODELTRANSLATION_INCLUDE_TRANSLATABLE: bool = False
    """Whether to add translatable fields to the GraphQL schema when using `django-modeltranslation`."""

    MODELTRANSLATION_INCLUDE_TRANSLATIONS: bool = True
    """Whether to add translation fields to the GraphQL schema when using `django-modeltranslation`."""

    # Optimizer

    DISABLE_ONLY_FIELDS_OPTIMIZATION: bool = False
    """Disable optimizing fetched fields with `queryset.only()`."""

    OPTIMIZER_CLASS: type[QueryOptimizer] = "undine.optimizer.optimizer.QueryOptimizer"  # type: ignore[assignment]
    """The optimizer class to use for optimizing queries."""

    PREFETCH_HACK_CACHE_KEY: str = "_undine_prefetch_hack_cache"
    """The key to use for storing the prefetch hack cache in the queryset hints."""

    # Argument & parameter names

    MUTATION_INPUT_DATA_KEY: str = "input"
    """The key used for the input argument of a MutationType."""

    QUERY_TYPE_FILTER_INPUT_KEY: str = "filter"
    """The key used for the filter argument of QueryType."""

    QUERY_TYPE_ORDER_INPUT_KEY: str = "orderBy"
    """The key used for the order by argument of a `QueryType`."""

    RESOLVER_ROOT_PARAM_NAME: str = "root"
    """The name of the root/parent parameter in resolvers."""

    TOTAL_COUNT_PARAM_NAME: str = "totalCount"
    """The name of the total count parameter in connection resolvers."""

    # Other

    DOCSTRING_PARSER: type[DocstringParserProtocol] = "undine.parsers.parse_docstring.RSTDocstringParser"  # type: ignore[assignment]
    """The docstring parser to use."""

    SDL_PRINTER: type[SDLPrinter] = "undine.utils.graphql.sdl_printer.SDLPrinter"  # type: ignore[assignment]
    """The SDL printer to use."""

    PG_TEXT_SEARCH_PREFIX: str = "_undine_ts_vector"
    """A prefix to use for the filter aliases of postgres full text search Filters."""

    EMPTY_VALUES: Container[Any] = (None, "", [], {})
    """By default, if a Filter receives any of these values, it will be ignored."""

    # Extensions keys

    CALCULATION_ARGUMENT_EXTENSIONS_KEY: str = "undine_calculation_argument"
    """The key to use for storing the calculation in the extensions of the GraphQL type."""

    CONNECTION_EXTENSIONS_KEY: str = "undine_connection"
    """The key to use for storing the connection in the extensions of the GraphQL type."""

    OFFSET_PAGINATION_EXTENSIONS_KEY: str = "undine_offset_pagination"
    """The key to use for storing the offset pagination in the extensions of the GraphQL field."""

    DIRECTIVE_ARGUMENT_EXTENSIONS_KEY: str = "undine_directive_argument"
    """The key used to store a Directive argument in the GraphQL extensions."""

    DIRECTIVE_EXTENSIONS_KEY: str = "undine_directive"
    """The key used to store a Directive in the GraphQL extensions."""

    ENTRYPOINT_EXTENSIONS_KEY: str = "undine_entrypoint"
    """The key used to store an Entrypoint in the field GraphQL extensions."""

    FIELD_EXTENSIONS_KEY: str = "undine_field"
    """The key used to store a Field in the field GraphQL extensions."""

    FILTER_EXTENSIONS_KEY: str = "undine_filter"
    """The key used to store a `Filter` in the argument GraphQL extensions."""

    FILTERSET_EXTENSIONS_KEY: str = "undine_filterset"
    """The key used to store a FilterSet in the argument GraphQL extensions."""

    INPUT_EXTENSIONS_KEY: str = "undine_input"
    """The key used to store an `Input` in the argument GraphQL extensions."""

    INTERFACE_FIELD_EXTENSIONS_KEY: str = "undine_interface_field"
    """The key used to store an `InterfaceField` in the field GraphQL extensions."""

    INTERFACE_TYPE_EXTENSIONS_KEY: str = "undine_interface"
    """The key used to store a `InterfaceType` in the object type GraphQL extensions."""

    MUTATION_TYPE_EXTENSIONS_KEY: str = "undine_mutation_type"
    """The key used to store a `MutationType` in the argument GraphQL extensions."""

    ORDER_EXTENSIONS_KEY: str = "undine_order"
    """The key used to store an `Order` in the argument GraphQL extensions."""

    ORDERSET_EXTENSIONS_KEY: str = "undine_orderset"
    """The key used to store a `OrderSet` in the argument GraphQL extensions."""

    QUERY_TYPE_EXTENSIONS_KEY: str = "undine_query_type"
    """The key used to store a `QueryType` in the object type GraphQL extensions."""

    ROOT_TYPE_EXTENSIONS_KEY: str = "undine_root_type"
    """The key used to store a `RootType` in the object type GraphQL extensions."""

    SCALAR_EXTENSIONS_KEY: str = "undine_scalar"
    """The key used to store a `Scalar` in the scalar GraphQL extensions."""

    SCHEMA_DIRECTIVES_EXTENSIONS_KEY: str = "undine_schema_directives"
    """The key used to store the schema directives in the schema GraphQL extensions."""

    UNION_TYPE_EXTENSIONS_KEY: str = "undine_union_type"
    """The key used to store a `UnionType` in the argument GraphQL extensions."""


DEFAULTS: dict[str, Any] = UndineDefaultSettings()._asdict()

IMPORT_STRINGS: set[str | bytes] = {
    "ADDITIONAL_VALIDATION_RULES.0",
    "DOCSTRING_PARSER",
    "EXECUTION_CONTEXT_CLASS",
    "LIFECYCLE_HOOKS.0",
    "OPTIMIZER_CLASS",
    "PERSISTED_DOCUMENTS_PERMISSION_CALLBACK",
    "SCHEMA",
    "SDL_PRINTER",
    "WEBSOCKET_CONNECTION_INIT_HOOK",
    "WEBSOCKET_PING_HOOK",
    "WEBSOCKET_PONG_HOOK",
}


REMOVED_SETTINGS: dict[str, Any] = {
    "ENTRYPOINT_LIMIT_PER_MODEL": "LIST_ENTRYPOINT_LIMIT",
    "CONNECTION_PAGE_SIZE": "PAGINATION_PAGE_SIZE",
    "CONNECTION_START_INDEX_KEY": "PAGINATION_START_INDEX_KEY",
    "CONNECTION_STOP_INDEX_KEY": "PAGINATION_STOP_INDEX_KEY",
    "CONNECTION_INDEX_KEY": "PAGINATION_INDEX_KEY",
    "CONNECTION_TOTAL_COUNT_KEY": "PAGINATION_TOTAL_COUNT_KEY",
    "OPERATION_HOOKS": "LIFECYCLE_HOOKS",
    "PARSE_HOOKS": "LIFECYCLE_HOOKS",
    "VALIDATION_HOOKS": "LIFECYCLE_HOOKS",
    "EXECUTION_HOOKS": "LIFECYCLE_HOOKS",
    "MIDDLEWARE": "LIFECYCLE_HOOKS",
}

undine_settings: UndineDefaultSettings = SettingsHolder(  # type: ignore[assignment]
    setting_name=SETTING_NAME,
    defaults=DEFAULTS,
    import_strings=IMPORT_STRINGS,
    removed_settings=REMOVED_SETTINGS,
)

reload_my_settings = reload_settings(SETTING_NAME, undine_settings)  # type: ignore[arg-type]
setting_changed.connect(reload_my_settings)


# Placeholder schema
example_schema = GraphQLSchema(
    query=GraphQLObjectType(
        "Query",
        fields={
            "testing": GraphQLField(
                GraphQLString,
                resolve=lambda obj, info: "Hello World",  # noqa: ARG005
            ),
        },
    ),
)
