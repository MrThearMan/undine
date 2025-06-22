"""Django settings for Undine. Can be configured in the Django settings file with the key 'UNDINE'."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from django.test.signals import setting_changed
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString
from settings_holder import SettingsHolder, reload_settings

if TYPE_CHECKING:
    from graphql import ASTValidationRule, ExecutionContext, GraphQLFieldResolver

    from undine.hooks import LifecycleHook
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.typing import DocstringParserProtocol
    from undine.utils.graphql.sdl_printer import SDLPrinter


__all__ = [
    "undine_settings",
]


SETTING_NAME: str = "UNDINE"


class UndineDefaultSettings(NamedTuple):
    """Default settings for Undine."""

    # Required

    SCHEMA: GraphQLSchema = "undine.settings.example_schema"  # type: ignore[assignment]
    """The schema to use for the GraphQL API."""

    GRAPHQL_PATH: str = "graphql/"
    """The path where the GraphQL endpoint is located by default."""

    GRAPHQL_VIEW_NAME: str = "graphql"
    """The name of given to the GraphQL view in the URLconf."""

    # Flags

    ALLOW_DID_YOU_MEAN_SUGGESTIONS: bool = False
    """Whether to allow the 'did you mean' suggestions on error messages."""

    ALLOW_INTROSPECTION_QUERIES: bool = False
    """Whether schema introspection queries are allowed or not."""

    CAMEL_CASE_SCHEMA_FIELDS: bool = True
    """Should names be converted from 'snake_case' to 'camelCase' for the GraphQL schema?"""

    FILE_UPLOAD_ENABLED: bool = False
    """Whether file uploads are enabled. Should enable CSRF protection on the GraphiQL endpoint if enabled."""

    MUTATION_FULL_CLEAN: bool = True
    """Whether to run `model.full_clean()` when mutating a model."""

    PERSISTED_DOCUMENTS_ONLY: bool = False
    """Whether to only allow persisted documents to be executed."""

    # Limits

    CONNECTION_PAGE_SIZE: int | None = 100
    """The maximum number of items to return in a page of a Connection."""

    ENTRYPOINT_LIMIT_PER_MODEL: int = 100
    """Default number of objects that are fetched per model when fetching results in an abstract type Entrypoint."""

    MAX_FILTERS_PER_TYPE: int = 20
    """The maximum number of filters allowed for a single `FilterSet`."""

    MAX_ORDERS_PER_TYPE: int = 10
    """The maximum number of orders allowed for a single `OrderSet`."""

    # GraphQL execution

    ADDITIONAL_VALIDATION_RULES: list[type[ASTValidationRule]] = []
    """Additional validation rules to use for validating the GraphQL schema."""

    EXECUTION_CONTEXT_CLASS: type[ExecutionContext] = "undine.execution.UndineExecutionContext"  # type: ignore[assignment]
    """GraphQL execution context class used by the schema."""

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

    MIDDLEWARE: list[GraphQLFieldResolver] = []
    """Middleware to use in GraphQL field resolving."""

    MUTATION_INSTANCE_LIMIT: int = 100
    """The maximum number of objects that can be mutated in a single mutation."""

    NO_ERROR_LOCATION: bool = False
    """Whether to add the location information to GraphQL errors."""

    ROOT_VALUE: Any = None
    """The root value for the GraphQL execution."""

    # Hooks

    OPERATION_HOOKS: list[type[LifecycleHook]] = []
    """Hooks to run during the operation."""

    PARSE_HOOKS: list[type[LifecycleHook]] = []
    """Hooks to run during parsing the GraphQL request."""

    VALIDATION_HOOKS: list[type[LifecycleHook]] = []
    """Hooks to run during validation the GraphQL request."""

    EXECUTION_HOOKS: list[type[LifecycleHook]] = []
    """Hooks to run during execution the GraphQL request."""

    # Testing client

    TESTING_CLIENT_FULL_STACKTRACE: bool = False
    """Whether to include the full stacktrace in testing client instead of just the relevant frames."""

    # GraphiQL

    GRAPHIQL_ENABLED: bool = False
    """Is GraphiQL enabled?"""

    GRAPHIQL_PLUGIN_EXPLORER_VERSION: str = "3.2.5"
    """The version of the plugin explorer to use for GraphiQL."""

    GRAPHIQL_REACT_VERSION: str = "18.3.1"
    """The version of React to use for GraphiQL."""

    GRAPHIQL_VERSION: str = "3.8.3"
    """The version of GraphiQL to use."""

    # Django-modeltranslation

    MODELTRANSLATION_INCLUDE_TRANSLATABLE: bool = False
    """Whether to add translatable fields to the GraphQL schema when using `django-modeltranslation`."""

    MODELTRANSLATION_INCLUDE_TRANSLATIONS: bool = True
    """Whether to add translation fields to the GraphQL schema when using `django-modeltranslation`."""

    # Optimizer

    CONNECTION_START_INDEX_KEY: str = "_undine_pagination_start"
    """The key to which the connection's pagination start index is annotated to or added to in the queryset hints."""

    CONNECTION_STOP_INDEX_KEY: str = "_undine_pagination_stop"
    """The key to which the connection's pagination stop index is annotated to or added to in the queryset hints."""

    CONNECTION_INDEX_KEY: str = "_undine_pagination_index"
    """The key to which nested connection node's pagination index is annotated to the queryset."""

    CONNECTION_TOTAL_COUNT_KEY: str = "_undine_pagination_total_count"
    """The key to which the connection's total count annotated to or added to in the queryset hints."""

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

    # Extensions keys

    CALCULATION_ARGUMENT_EXTENSIONS_KEY: str = "undine_calculation_argument"
    """The key to use for storing the calculation in the extensions of the GraphQL type."""

    CONNECTION_EXTENSIONS_KEY: str = "undine_connection"
    """The key to use for storing the connection in the extensions of the GraphQL type."""

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
    "EXECUTION_HOOKS.0",
    "MIDDLEWARE.0",
    "OPERATION_HOOKS.0",
    "OPTIMIZER_CLASS",
    "PARSE_HOOKS.0",
    "SCHEMA",
    "SDL_PRINTER",
    "VALIDATION_HOOKS.0",
}

undine_settings: UndineDefaultSettings = SettingsHolder(  # type: ignore[assignment]
    setting_name=SETTING_NAME,
    defaults=DEFAULTS,
    import_strings=IMPORT_STRINGS,
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
