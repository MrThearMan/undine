"""Django settings for Undine. Can be configured in the Django settings file with the key 'UNDINE'."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from django.core.cache import DEFAULT_CACHE_ALIAS
from django.test.signals import setting_changed
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString
from settings_holder import SettingsHolder, reload_settings

if TYPE_CHECKING:
    from collections.abc import Callable, Container

    from ddtrace.trace import Span as DatadogSpan
    from graphql import ASTValidationRule, GraphQLError
    from opentelemetry.trace import Span as OpenTelemetrySpan

    from undine.execution import UndineExecutor
    from undine.hooks import LifecycleHook, LifecycleHookContext
    from undine.integrations.sentry import RecordedSpan as SentryRecordedSpan
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

    PAGINATION_ORDERING_KEY: str = "_undine_pagination_ordering"
    """The key prefix to which cursor pagination annotates ordering values that are not plain columns."""

    PAGINATION_MEMBER_RANK_KEY: str = "_undine_pagination_member_rank"
    """The key to which a union/interface member's own per-implementation order is annotated as a rank."""

    PAGINATION_TOTAL_COUNT_KEY: str = "_undine_pagination_total_count"
    """The key to which the connection's total count annotated to or added to in the queryset hints."""

    # GraphQL execution

    ADDITIONAL_VALIDATION_RULES: list[type[ASTValidationRule]] = []
    """Additional validation rules to use for validating the GraphQL schema."""

    EXECUTOR_CLASS: type[UndineExecutor] = "undine.execution.UndineExecutor"  # type: ignore[assignment]
    """GraphQL executor class used by the schema."""

    LIFECYCLE_HOOKS: list[type[LifecycleHook]] = [
        "undine.hooks.RequestCacheHook",  # type: ignore[list-item]
        "undine.hooks.VisibilityCacheHook",  # type: ignore[list-item]
        "undine.hooks.AtomicMutationHook",  # type: ignore[list-item]
    ]
    """Lifecycle hooks to use during GraphQL operations."""

    MAX_ALLOWED_ALIASES: int = 15
    """The maximum number of aliases allowed in a single operation."""

    MAX_ALLOWED_DIRECTIVES: int = 50
    """The maximum number of directives allowed in a single operation."""

    MAX_ERRORS: int = 100
    """The maximum number of validation errors allowed in a GraphQL request before it is rejected."""

    MAX_LIST_NESTING_DEPTH: int = 5
    """The maximum number of to-many relations that can be nested inside one another in a single operation."""

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

    # Error handling

    ERROR_MASKING_MESSAGE: str = "Unexpected error."
    """The message sent to the client in place of a masked error's own message."""

    ERROR_MASKING_PREDICATE: Callable[[GraphQLError], bool] = "undine.utils.graphql.utils.should_mask_error"  # type: ignore[assignment]
    """Function to use for checking whether an error should be masked before it's sent to the client."""

    # Testing client

    TESTING_CLIENT_FULL_STACKTRACE: bool = False
    """Whether to include the full stacktrace in testing client instead of just the relevant frames."""

    TESTING_CLIENT_NO_ASYNC_TIMEOUT: bool = False
    """Whether to disable the websocket timeouts in testing client."""

    # GraphiQL

    GRAPHIQL_ENABLED: bool = False
    """Is GraphiQL enabled?"""

    GRAPHIQL_SSE_ENABLED: bool = False
    """Whether GraphiQL uses SSE for subscriptions instead of the built-in WebSocket client."""

    GRAPHIQL_SSE_SINGLE_CONNECTION: bool = False
    """Controls whether the SSE subscription client uses single connection mode."""

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

    # multipart/mixed HTTP

    ALLOW_QUERIES_WITH_MULTIPART_MIXED: bool = False
    """Whether queries can be executed over multipart/mixed HTTP requests."""

    ALLOW_MUTATIONS_WITH_MULTIPART_MIXED: bool = False
    """Whether mutations can be executed over multipart/mixed HTTP requests."""

    MULTIPART_MIXED_HEARTBEAT_INTERVAL: int = 12
    """Interval in seconds for multipart/mixed HTTP heartbeats. Set to 0 to disable."""

    # Incremental delivery over HTTP

    EXPERIMENTAL_INCREMENTAL_DELIVERY: bool = False
    """Whether to enable experimental support for incremental delivery over HTTP."""

    INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL: int = 0
    """
    Interval in seconds for incremental delivery over HTTP heartbeats. Set to 0 to disable.
    Disabled by default, since heartbeats are not part of the incremental delivery over HTTP spec,
    and clients might not handle them correctly.
    """

    # Federation

    FEDERATION_VERSION: str = "2.15"
    """The Apollo Federation 2 spec version used by `create_federation_schema`."""

    FEDERATION_SDL_EXTENSIONS_KEY: str = "undine_federation_sdl"
    """The key on `schema.extensions` where the pre-computed federation SDL string is cached."""

    FEDERATION_BUILTIN_EXTENSIONS_KEY: str = "undine_federation_builtin"
    """The key set to `True` on the extensions of federation builtins for programmatic identification."""

    FEDERATION_MIN_VERSION_EXTENSIONS_KEY: str = "undine_federation_min_version"
    """The key on `directive.extensions` storing the minimum federation version a builtin directive requires."""

    FEDERATION_TYPE_EXTENSIONS_KEY: str = "undine_federation_type"
    """The key used to store a `FederationType` in the object type GraphQL extensions."""

    FEDERATION_FIELD_EXTENSIONS_KEY: str = "undine_federation_field"
    """The key used to store a `FederationField` in the field GraphQL extensions."""

    # Django-modeltranslation

    MODELTRANSLATION_INCLUDE_TRANSLATABLE: bool = False
    """Whether to add translatable fields to the GraphQL schema when using `django-modeltranslation`."""

    MODELTRANSLATION_INCLUDE_TRANSLATIONS: bool = True
    """Whether to add translation fields to the GraphQL schema when using `django-modeltranslation`."""

    # OpenTelemetry

    OPENTELEMETRY_VARIABLES_CALLBACK: Callable[[LifecycleHookContext], dict[str, Any]] = (  # type: ignore[assignment]
        "undine.integrations.opentelemetry.no_traced_variables"  # type: ignore[assignment]
    )
    """Function that returns the GraphQL variables that are attached to OpenTelemetry operation spans."""

    OPENTELEMETRY_SPAN_CALLBACK: Callable[[OpenTelemetrySpan, LifecycleHookContext], None] = (  # type: ignore[assignment]
        "undine.integrations.opentelemetry.no_op_span_callback"  # type: ignore[assignment]
    )
    """Function called with the OpenTelemetry operation span so it can add its own attributes to it."""

    # Datadog

    DATADOG_SERVICE_NAME: str = "undine"
    """The Datadog service name recorded on spans created by the Datadog lifecycle hooks."""

    DATADOG_SPAN_CALLBACK: Callable[[DatadogSpan, LifecycleHookContext], None] = (  # type: ignore[assignment]
        "undine.integrations.datadog.no_op_span_callback"  # type: ignore[assignment]
    )
    """Function called with the Datadog operation span so it can add its own tags to it."""

    DATADOG_VARIABLES_CALLBACK: Callable[[LifecycleHookContext], dict[str, Any]] = (  # type: ignore[assignment]
        "undine.integrations.datadog.no_traced_variables"  # type: ignore[assignment]
    )
    """Function that returns the GraphQL variables that are attached to Datadog operation spans."""

    # Sentry

    SENTRY_REPORT_ERROR_PREDICATE: Callable[[GraphQLError], bool] = (  # type: ignore[assignment]
        "undine.integrations.sentry.report_server_errors"  # type: ignore[assignment]
    )
    """Function to use for checking if a GraphQL error should be reported to Sentry as an issue."""

    SENTRY_SPAN_CALLBACK: Callable[[SentryRecordedSpan, LifecycleHookContext], None] = (  # type: ignore[assignment]
        "undine.integrations.sentry.no_op_span_callback"  # type: ignore[assignment]
    )
    """Function called with each span the Sentry lifecycle hook records so it can add attributes to it."""

    SENTRY_VARIABLES_CALLBACK: Callable[[LifecycleHookContext], dict[str, Any]] = (  # type: ignore[assignment]
        "undine.integrations.sentry.redacted_variables"  # type: ignore[assignment]
    )
    """Function that returns the GraphQL variables that are attached to Sentry operation spans."""

    SENTRY_SKIP_FIELD_SPANS_PREDICATE: Callable[[LifecycleHookContext], bool] = (  # type: ignore[assignment]
        "undine.integrations.sentry.skip_introspection_queries"  # type: ignore[assignment]
    )
    """Function to use for checking if an operation should be recorded without its field spans."""

    # Optimizer

    DISABLE_ONLY_FIELDS_OPTIMIZATION: bool = False
    """Disable optimizing fetched fields with `queryset.only()`."""

    OPTIMIZER_CLASS: type[QueryOptimizer] = "undine.optimizer.optimizer.QueryOptimizer"  # type: ignore[assignment]
    """The optimizer class to use for optimizing queries."""

    PREFETCH_HACK_CACHE_KEY: str = "_undine_prefetch_hack_cache"
    """The key to use for storing the prefetch hack cache in the queryset hints."""

    # Caching

    ENTRYPOINT_DEFAULT_CACHE_TIME: int = 0
    """The default caching time an `Entrypoint` for the @cacheRules directive."""

    REQUEST_CACHE_ALIAS: str = DEFAULT_CACHE_ALIAS
    """The cache alias to use for caching requests."""

    REQUEST_CACHE_EXTRA_CONTEXT: Callable[[LifecycleHookContext], dict[str, Any]] = "undine.hooks.default_extra_context"  # type: ignore[assignment]
    """Function to use for extra context to add to the cache key."""

    REQUEST_CACHE_READ_PREDICATE: Callable[[LifecycleHookContext], bool] = "undine.hooks.should_read_from_cache"  # type: ignore[assignment]
    """Function to use for checking if the result should be read from cache."""

    REQUEST_CACHE_WRITE_PREDICATE: Callable[[LifecycleHookContext], bool] = "undine.hooks.should_write_to_cache"  # type: ignore[assignment]
    """Function to use for checking if the result should be written to cache."""

    REQUEST_CACHE_PREFIX: str = "undine-cache"
    """The prefix to use for the cache keys of requests."""

    # Visibility

    VISIBILITY_ACTIVE_EXTENSIONS_KEY: str = "undine_visibility_active"
    """The key set to `True` on `schema.extensions` when the schema uses visibility checks."""

    VISIBILITY_CACHE_ALIAS: str = DEFAULT_CACHE_ALIAS
    """The cache alias to use for visibility caching."""

    VISIBILITY_CACHE_TIMEOUT: int = 0
    """How many seconds to cache the filtered introspection payload per user. `0` disables the cross-request cache."""

    VISIBILITY_CACHE_PREFIX: str = "undine_visibility"
    """The prefix to use for cross-request visibility cache keys."""

    VISIBILITY_CACHE_EXTRA_CONTEXT: Callable[[Any], Any] = "undine.utils.visibility.default_visibility_extra_context"  # type: ignore[assignment]
    """Function that returns extra context added to the visibility cache key."""

    VISIBILITY_MEMO_ATTRIBUTE: str = "_undine_visibility_memo"
    """The attribute on the request where visibility check results are memoized for the duration of the request."""

    # Argument & parameter names

    MUTATION_INPUT_DATA_KEY: str = "input"
    """The key used for the input argument of a MutationType."""

    MUTATION_INPUT_DATA_TYPES_MODULE: str | None = None
    """
    Dotted module path where the `generate_mutation_input_types` management command writes
    the generated `TypedDicts` for each `MutationType.__input_map__`. Not imported at runtime,
    only used as a write target for the code generator.
    """

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
    "DATADOG_SPAN_CALLBACK",
    "DATADOG_VARIABLES_CALLBACK",
    "DOCSTRING_PARSER",
    "ERROR_MASKING_PREDICATE",
    "EXECUTOR_CLASS",
    "LIFECYCLE_HOOKS.0",
    "OPENTELEMETRY_SPAN_CALLBACK",
    "OPENTELEMETRY_VARIABLES_CALLBACK",
    "OPTIMIZER_CLASS",
    "PERSISTED_DOCUMENTS_PERMISSION_CALLBACK",
    "REQUEST_CACHE_EXTRA_CONTEXT",
    "REQUEST_CACHE_READ_PREDICATE",
    "REQUEST_CACHE_WRITE_PREDICATE",
    "SCHEMA",
    "SDL_PRINTER",
    "VISIBILITY_CACHE_EXTRA_CONTEXT",
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
    "EXECUTION_CONTEXT_CLASS": "EXECUTOR_CLASS",
    "EXPERIMENTAL_VISIBILITY_CHECKS": None,
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
