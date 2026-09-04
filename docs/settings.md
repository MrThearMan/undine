description: Documentation on Undine various settings.

# Settings

In this section, we'll cover the settings that can be used to customize Undine.
Settings should be set in a dictionary named `UNDINE` in your settings file, unless otherwise specified.
The settings can also be found in the [settings file]{:target="_blank"}.

```python
UNDINE = {
    # Settings go here
}
```

[settings file]: https://github.com/MrThearMan/undine/blob/main/undine/settings.py

/// details | `ADDITIONAL_LIFECYCLE_HOOKS`
    attrs: {id: additional_lifecycle_hooks}

Type: `list[type[LifecycleHook]]` | Default: `[]`

Lifecycle hooks to use during GraphQL operations in addition to the built-in ones.
Values should be given as the dotted paths to the lifecycle hooks used.
Each hook runs at the point set by its `priority`, so the order of this list does not matter.
See [Lifecycle Hooks](lifecycle-hooks.md) for more information.

///

/// details | `ADDITIONAL_VALIDATION_RULES`
    attrs: {id: additional_validation_rules}

Type: `list[type[ASTValidationRule]]` | Default: `[]`

Additional validation rules to use for validating GraphQL documents (i.e. "requests").
Values should be given as the dotted paths to the validation rules used.

///

/// details | `ALLOW_DID_YOU_MEAN_SUGGESTIONS`
    attrs: {id: allow_did_you_mean_suggestions}

Type: `bool` | Default: `False`

Whether to allow the _'did you mean'_ suggestions on error messages.
Disabled by default so that information on the schema structure cannot
be gained from error messages when trying to find schema entrypoints through
trial and error (a form of security through obscurity).

Automatically forced to `False` when a schema uses [visibility](visibility.md).

///

/// details | `ALLOW_INTROSPECTION_QUERIES`
    attrs: {id: allow_introspection_queries}

Type `bool` | Default: `False`

Whether schema introspection queries are allowed or not.
Disabled by default so that information on the schema structure cannot
be gained through introspection (a form of security through obscurity).

Should set this to `True` if using [GraphiQL](integrations.md#graphiql).

///

/// details | `ALLOW_QUERIES_WITH_MULTIPART_MIXED`
    attrs: {id: allow_queries_with_multipart_mixed}

Type: `bool` | Default: `False`

Whether queries can be executed over multipart/mixed HTTP requests.

///

/// details | `ALLOW_QUERIES_WITH_SSE`
    attrs: {id: allow_queries_with_sse}

Type: `bool` | Default: `False`

Whether queries can be executed over Server-Sent Events.

///

/// details | `ALLOW_MUTATIONS_WITH_MULTIPART_MIXED`
    attrs: {id: allow_mutations_with_multipart_mixed}

Type: `bool` | Default: `False`

Whether mutations can be executed over multipart/mixed HTTP requests.

///

/// details | `ALLOW_MUTATIONS_WITH_SSE`
    attrs: {id: allow_mutations_with_sse}

Type: `bool` | Default: `False`

Whether mutations can be executed over Server-Sent Events.

///

/// details | `ALLOW_QUERIES_WITH_WEBSOCKETS`
    attrs: {id: allow_queries_with_websockets}

Type: `bool` | Default: `False`

Whether queries can be executed over WebSockets.

///

/// details | `ALLOW_MUTATIONS_WITH_WEBSOCKETS`
    attrs: {id: allow_mutations_with_websockets}

Type: `bool` | Default: `False`

Whether mutations can be executed over WebSockets.

///

/// details | `ASYNC`
    attrs: {id: async}

Type `bool` | Default: `False`

Whether to use async view for the GraphQL endpoint or not.
See Undine's [Async](async.md) documentation for more information.

///

/// details | `AUTOGENERATION`
    attrs: {id: autogeneration}

Type `bool` | Default: `False`

Whether to automatically generate `Fields` for `QueryTypes`, `Inputs` for `MutationTypes`,
`Filters` for `FilterSets`, and `Orders` for `OrderSets`. Can also be set on an individual
`QueryType`, `MutationType`, `FilterSet`, and `OrderSet` classes.

///

/// details | `AUTOMATIC_PERSISTED_QUERIES`
    attrs: {id: automatic_persisted_queries}

Type `bool` | Default: `False`

Whether clients can register persisted documents during the request phase using the APQ protocol.
See [automatic persisted queries](persisted-documents.md#automatic-persisted-queries) for more information.

///

/// details | `CALCULATION_ARGUMENT_EXTENSIONS_KEY`
    attrs: {id: calculation_argument_extensions_key}

Type: `str` | Default: `"undine_calculation_argument"`

The key used to store a `CalculationArgument` in the `extensions` of its `GraphQLArgument`.

///

/// details | `CAMEL_CASE_SCHEMA_FIELDS`
    attrs: {id: camel_case_schema_fields}

Type: `bool` | Default: `True`

Should field names be converted from _'snake_case'_ to _'camelCase'_ for the GraphQL schema?
Conversion is not applied if `schema_name` is set manually in on the `Entrypoint`, `Field`, `Input`, etc.

///

/// details | `CONNECTION_EXTENSIONS_KEY`
    attrs: {id: connection_extensions_key}

Type: `str` | Default: `"undine_connection"`

The key used to store a `Connection` in the `extensions` of its `GraphQLObjectType`.

///

/// details | `DATADOG_SERVICE_NAME`
    attrs: {id: datadog_service_name}

Type: `str` | Default: `"undine"`

The Datadog service name recorded on spans created by the Datadog lifecycle hooks.
See [Datadog](integrations.md#datadog) for more information.

///

/// details | `DATADOG_SKIP_FIELD_SPANS_PREDICATE`
    attrs: {id: datadog_skip_field_spans_predicate}

Type: `Callable[[LifecycleHookContext], bool]` | Default: `"undine.integrations.datadog.skip_introspection_queries"`

Function to use for checking if an operation should be recorded without its field spans.
By default, introspection queries are recorded without them, since they resolve a field for
every type and field in the schema.
See [Datadog](integrations.md#datadog) for more information.
Value should be given as the dotted path to the function.

///

/// details | `DATADOG_SPAN_CALLBACK`
    attrs: {id: datadog_span_callback}

Type: `Callable[[Span, LifecycleHookContext], None]` | Default: `"undine.integrations.datadog.no_op_span_callback"`

Function called with each span the Datadog lifecycle hook records so it can add its own
tags to it. By default, no tags are added. See [Datadog](integrations.md#datadog) for more information.
Value should be given as the dotted path to the function.

///

/// details | `DATADOG_VARIABLES_CALLBACK`
    attrs: {id: datadog_variables_callback}

Type: `Callable[[LifecycleHookContext], dict[str, Any]]` | Default: `"undine.integrations.datadog.redacted_variables"`

Function that returns the GraphQL variables that are attached to Datadog operation spans.
By default, the name of each variable is attached with its value redacted,
since the values can contain sensitive data.
See [Datadog](integrations.md#datadog) for more information.
Value should be given as the dotted path to the function.

///

/// details | `DIRECTIVE_ARGUMENT_EXTENSIONS_KEY`
    attrs: {id: directive_argument_extensions_key}

Type: `str` | Default: `"undine_directive_argument"`

The key used to store a `DirectiveArgument` in the `extensions` of its `GraphQLArgument`.

///

/// details | `DIRECTIVE_EXTENSIONS_KEY`
    attrs: {id: directive_extensions_key}

Type `str` | Default: `"undine_directive"`

The key used to store a `Directive` in the `extensions` of its `GraphQLDirective`.

///

/// details | `DISABLE_ONLY_FIELDS_OPTIMIZATION`
    attrs: {id: disable_only_fields_optimization}

Type `bool` | Default: `False`

Disable optimizing fetched fields with `queryset.only()`.

///

/// details | `DOCSTRING_PARSER`
    attrs: {id: docstring_parser}

Type `type[DocstringParserProtocol]` | Default: `"undine.parsers.parse_docstring.RSTDocstringParser"`

The docstring parser to use to parse function docstrings to schema descriptions.
Should be given as the dotted path to the docstring parser class.

///

/// details | `EMPTY_VALUES`
    attrs: {id: empty_values}

Type `Container[Any]` | Default: `(None, "", [], {})`

By default, if a `Filter` receives any of these values, that filter will be ignored.
Can be changed on per-`Filter` basis using the [`empty_values`](filtering.md#empty-values) argument.

///

/// details | `ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`
    attrs: {id: enable_class_attribute_docstrings}

Type `bool` | Default: `False`

Whether to parse class attribute docstrings or not.
Disabled by default to improve performance of the schema creation.

///

/// details | `ENTRYPOINT_DEFAULT_CACHE_TIME`
    attrs: {id: entrypoint_default_cache_time}

Type `int` | Default: `0`

How many seconds each `Entrypoint` of the `Query` root type can be cached for when it doesn't set
its own `cache_time`. Set to `0` (default) to cache no `Entrypoint` unless it asks for it.
See [response caching](caching.md#response-caching) for more information.

///

/// details | `ENTRYPOINT_EXTENSIONS_KEY`
    attrs: {id: entrypoint_extensions_key}

Type `str` | Default: `"undine_entrypoint"`

The key used to store an `Entrypoint` in the `extensions` of its `GraphQLField`.

///

/// details | `ERROR_MASKING_MESSAGE`
    attrs: {id: error_masking_message}

Type: `str` | Default: `"Unexpected error."`

The message sent to the client in place of a masked error's own message.
See [`ERROR_MASKING_PREDICATE`](#error_masking_predicate) for which errors are masked.

///

/// details | `ERROR_MASKING_PREDICATE`
    attrs: {id: error_masking_predicate}

Type: `Callable[[GraphQLError], bool]` | Default: `"undine.utils.graphql.utils.should_mask_error"`

Function for checking whether an error should be masked before it's sent to the client.
Value should be given as the dotted path to the function.

By default, only genuinely unexpected errors are masked. An error is unexpected when it comes from
an exception that nobody raised for the client to see, like a `RuntimeError` from a resolver or a
database error from a Django call.

Deliberate errors reach the client unchanged. An error is deliberate when it's a `GraphQLError`,
whether you raised it yourself or Undine raised it for a server problem.

A masked error keeps its `path`, `locations` and `status_code`.
Its message is replaced with [`ERROR_MASKING_MESSAGE`](#error_masking_message),
and all of its other `extensions`, like `error_code`, are removed.

A masked error never includes a traceback in the response,
even if [`INCLUDE_ERROR_TRACEBACK`](#include_error_traceback) is enabled.

Masking only affects the response. The original message and traceback are always logged
to the `undine` logger.

To turn masking off, set this to `"undine.utils.graphql.utils.never_mask_error"`.

///

/// details | `EXECUTION_CONTEXT_CLASS`
    attrs: {id: execution_context_class}

Type `type[UndineExecutionContext]` | Default: `"undine.execution.UndineExecutionContext"`

GraphQL execution context class used by the schema.
Should be given as the dotted path to the execution context class.

///

/// details | `EXPERIMENTAL_INCREMENTAL_DELIVERY`
    attrs: {id: experimental_incremental_delivery}

Type: `bool` | Default: `False`

Whether to enable experimental support for incremental delivery over HTTP.

///

/// details | `FEDERATION_BUILTIN_EXTENSIONS_KEY`
    attrs: {id: federation_builtin_extensions_key}

Type: `str` | Default: `"undine_federation_builtin"`

Marker key set to `True` on the extensions of Apollo Federation builtin scalars and types.

///

/// details | `FEDERATION_FIELD_EXTENSIONS_KEY`
    attrs: {id: federation_field_extensions_key}

Type: `str` | Default: `"undine_federation_field"`

The key used to store a `FederationField` in the `extensions` of its `GraphQLField`.

///

/// details | `FEDERATION_MIN_VERSION_EXTENSIONS_KEY`
    attrs: {id: federation_min_version_extensions_key}

Type: `str` | Default: `"undine_federation_min_version"`

The key on the `extensions` of a builtin federation `Directive` that records the minimum
`FEDERATION_VERSION` at which the directive is available. Used by `create_federation_schema`
to reject directives applied on subgraphs pinned to an older federation version.

///

/// details | `FEDERATION_SDL_EXTENSIONS_KEY`
    attrs: {id: federation_sdl_extensions_key}

Type: `str` | Default: `"undine_federation_sdl"`

The key on schema extensions where the pre-computed federation SDL string is cached by
[`create_federation_schema`](federation.md#setup). The `_service` resolver reads from this key.

///

/// details | `FEDERATION_TYPE_EXTENSIONS_KEY`
    attrs: {id: federation_type_extensions_key}

Type: `str` | Default: `"undine_federation_type"`

The key used to store a `FederationType` in the `extensions` of its `GraphQLObjectType`.

///

/// details | `FEDERATION_VERSION`
    attrs: {id: federation_version}

Type: `str` | Default: `"2.15"`

The Apollo Federation 2 spec version used by [`create_federation_schema`](federation.md#setup). Must be one
of `"2.0"` through `"2.15"`.

///

/// details | `FIELD_EXTENSIONS_KEY`
    attrs: {id: field_extensions_key}

Type: `str` | Default: `"undine_field"`

The key used to store a `Field` in the `extensions` of its `GraphQLField`.

///

/// details | `FILE_UPLOAD_ENABLED`
    attrs: {id: file_upload_enabled}

Type: `bool` | Default: `False`

Whether file uploads are enabled. Should enable CSRF protection on the GraphiQL endpoint if enabled.
See [file uploads](file-upload.md) for more information.

///

/// details | `FILTER_EXTENSIONS_KEY`
    attrs: {id: filter_extensions_key}

Type: `str` | Default: `"undine_filter"`

The key used to store a `Filter` in the `extensions` of its `GraphQLInputField`.

///

/// details | `FILTERSET_EXTENSIONS_KEY`
    attrs: {id: filterset_extensions_key}

Type: `str` | Default: `"undine_filterset"`

The key used to store a `FilterSet` in the `extensions` of its `GraphQLInputObjectType`.

///

/// details | `GRAPHIQL_ENABLED`
    attrs: {id: graphiql_enabled}

Type: `bool` | Default: `False`

Whether to enable [GraphiQL](integrations.md#graphiql). Should also set [`ALLOW_INTROSPECTION_QUERIES`](#allow_introspection_queries)
to `True`, so that GraphiQL can introspect the GraphQL schema.

///

/// details | `GRAPHIQL_SSE_ENABLED`
    attrs: {id: graphiql_sse_enabled}

Type: `bool` | Default: `False`

Whether GraphiQL uses SSE for subscriptions instead of the built-in WebSocket client.

///

/// details | `GRAPHIQL_SSE_SINGLE_CONNECTION`
    attrs: {id: graphiql_sse_single_connection}

Type: `bool` | Default: `False`

Controls whether the SSE subscription client uses single connection mode.
Only relevant when [`GRAPHIQL_SSE_ENABLED`](#graphiql_sse_enabled) is enabled.

///

/// details | `GRAPHQL_PATH`
    attrs: {id: graphql_path}

Type: `str` | Default: `"graphql/"`

The URL path where the GraphQL endpoint is located
if it's included using `path("", include("undine.http.urls"))`.

///

/// details | `GRAPHQL_VIEW_NAME`
    attrs: {id: graphql_view_name}

Type: `str` | Default: `"graphql"`

The name given to the GraphQL view in Django's URL resolvers
if it's included using `path("", include("undine.http.urls"))`.

///

/// details | `INCLUDE_ERROR_TRACEBACK`
    attrs: {id: include_error_traceback}

Type: `bool` | Default: `False`

When a GraphQL request returns an error response,
and the error is based on a non-GraphQL exception,
if this setting is enabled, the error traceback will be included in the response.
Useful for debugging.

Masked errors never include a traceback in the response.
Turn masking off with [`ERROR_MASKING_PREDICATE`](#error_masking_predicate)
to see tracebacks for server errors.

///

/// details | `INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL`
    attrs: {id: incremental_delivery_heartbeat_interval}

Type: `int` | Default: `0`

Interval in seconds for incremental delivery over HTTP heartbeats. Set to 0 to disable.

Heartbeats are disabled by default, since they are not part of the incremental delivery over HTTP
specification, and clients are not required to handle them.

///

/// details | `INPUT_EXTENSIONS_KEY`
    attrs: {id: input_extensions_key}

Type: `str` | Default: `"undine_input"`

The key used to store an `Input` in the `extensions` of its `GraphQLInputField`.

///

/// details | `INTERFACE_FIELD_EXTENSIONS_KEY`
    attrs: {id: interface_field_extensions_key}

Type: `str` | Default: `"undine_interface_field"`

The key used to store an `InterfaceField` in the `extensions` of its `GraphQLField`.

///

/// details | `INTERFACE_TYPE_EXTENSIONS_KEY`
    attrs: {id: interface_type_extensions_key}

Type: `str` | Default: `"undine_interface"`

The key used to store a `InterfaceType` in the `extensions` of its `GraphQLInterfaceType`.

///

/// details | `LIST_ENTRYPOINT_LIMIT`
    attrs: {id: list_entrypoint_limit}

Type `int | None` | Default: `None`

Maximum number of objects that can be returned from a list `Entrypoint` when not using pagination.
If None, all items are fetched.

///

/// details | `MAX_ALLOWED_ALIASES`
    attrs: {id: max_allowed_aliases}

Type: `int` | Default: `15`

The maximum number of aliases allowed in a single operation.

///

/// details | `MAX_ALLOWED_DIRECTIVES`
    attrs: {id: max_allowed_directives}

Type: `int` | Default: `50`

The maximum number of directives allowed in a single operation.

///

/// details | `MAX_ERRORS`
    attrs: {id: max_errors}

Type: `int` | Default: `100`

The maximum number of validation errors allowed in a GraphQL request before it's rejected,
even if validation is still not complete.

///

/// details | `MAX_FILTERS_PER_TYPE`
    attrs: {id: max_filters_per_type}

Type: `int` | Default: `20`

The maximum number of filters allowed to be used for filtering a single `QueryType`.

///

/// details | `MAX_LIST_NESTING_DEPTH`
    attrs: {id: max_list_nesting_depth}

Type: `int` | Default: `5`

The maximum number of to-many relations that can be nested inside one another in a single operation.
Only to-many relations count towards this limit, since to-one relations don't multiply the number
of rows returned by the operation.
See the [`MaxListNestingDepthRule`](validation-rules.md#maxlistnestingdepthrule) documentation for more information.

///

/// details | `MAX_ORDERS_PER_TYPE`
    attrs: {id: max_orders_per_type}

Type: `int` | Default: `10`

The maximum number of orderings allowed to be used for ordering a single `QueryType`.

///

/// details | `MAX_QUERY_COMPLEXITY`
    attrs: {id: max_query_complexity}

Type: `int` | Default: `10`

Maximum query complexity that is allowed to be queried in a single operation.
See the [field complexity](queries.md#complexity) documentation for more information.

///

/// details | `MAX_TOKENS`
    attrs: {id: max_tokens}

Type `int` | Default: `None`

Maximum number of [GraphQL document tokens]{:target="_blank"} the GraphQL parser will
parse before it rejects a request. By default, this is set to `None` which means no limit.

[GraphQL document tokens]: https://github.com/graphql-python/graphql-core/blob/main/src/graphql/language/token_kind.py

///

/// details | `MODELTRANSLATION_INCLUDE_TRANSLATABLE`
    attrs: {id: modeltranslation_include_translatable}

Type: `bool` | Default: `False`

Whether to add translatable fields to the GraphQL schema when using `django-modeltranslation`.
See [the integration description](integrations.md#django-model-translation) for more information.

///

/// details | `MODELTRANSLATION_INCLUDE_TRANSLATIONS`
    attrs: {id: modeltranslation_include_translations}

Type: `bool` | Default: `True`

Whether to add translation fields to the GraphQL schema when using `django-modeltranslation`.
See [the integration description](integrations.md#django-model-translation) for more information.

///

/// details | `MULTIPART_MIXED_HEARTBEAT_INTERVAL`
    attrs: {id: multipart_mixed_heartbeat_interval}

Type: `int` | Default: `12`

Interval in seconds for multipart/mixed HTTP heartbeats. Set to 0 to disable.

///

/// details | `MUTATION_FULL_CLEAN`
    attrs: {id: mutation_full_clean}

Type: `bool` | Default: `True`

Whether to run `model.full_clean()` when creating or updating Model using `MutationTypes`.
Turning this off can reduce the number of database queries during mutations,
but may introduce issues that would be solved by running full Model validation.

///

/// details | `MUTATION_INSTANCE_LIMIT`
    attrs: {id: mutation_instance_limit}

Type: `int` | Default: `100`

The maximum number of objects that can be mutated in a single bulk mutation.

///

/// details | `MUTATION_INPUT_DATA_KEY`
    attrs: {id: mutation_input_data_key}

Type: `str` | Default: `"input"`

The key that the input argument based on a `MutationType` is added to
when said `MutationType` is used in `Entrypoints`.

///

/// details | `MUTATION_INPUT_DATA_TYPES_MODULE`
    attrs: {id: mutation_input_data_types_module}

Type: `str | None` | Default: `None`

Dotted module path where the [`test_generate_mutation_input_types`](mutations.md#generating-input-data-types)
management command writes the generated `TypedDicts` for each `MutationType.__input_map__`.
For example, `"myproj.gql_input_types"` writes to `myproj/gql_input_types.py`.

The setting is a write target only; it is not imported at runtime. Set it to a module path
under one of your Python packages before running the management command.

///

/// details | `MUTATION_TYPE_EXTENSIONS_KEY`
    attrs: {id: mutation_type_extensions_key}

Type: `str` | Default: `"undine_mutation_type"`

The key used to store a `MutationType` in the `extensions` of its `GraphQLInputObjectType`.

///

/// details | `NO_ERROR_LOCATION`
    attrs: {id: no_error_location}

Type: `bool` | Default: `False`

Whether to remove error location information to GraphQL errors.

///

/// details | `OFFSET_PAGINATION_EXTENSIONS_KEY`
    attrs: {id: offset_pagination_extensions_key}

Type: `str` | Default: `"undine_offset_pagination"`

The key used to store an `OffsetPagination` in the `extensions` of its `GraphQLObjectType`.

///

/// details | `OPENTELEMETRY_SKIP_FIELD_SPANS_PREDICATE`
    attrs: {id: opentelemetry_skip_field_spans_predicate}

Type: `Callable[[LifecycleHookContext], bool]` | Default: `"undine.integrations.opentelemetry.skip_introspection_queries"`

Function to use for checking if an operation should be recorded without its field spans.
By default, introspection queries are recorded without them, since they resolve a field for
every type and field in the schema.
See [OpenTelemetry](integrations.md#opentelemetry) for more information.
Value should be given as the dotted path to the function.

///

/// details | `OPENTELEMETRY_SPAN_CALLBACK`
    attrs: {id: opentelemetry_span_callback}

Type: `Callable[[Span, LifecycleHookContext], None]` | Default: `"undine.integrations.opentelemetry.no_op_span_callback"`

Function called with each span the OpenTelemetry lifecycle hook records so it can add its own
attributes to it. By default, no attributes are added. See [OpenTelemetry](integrations.md#opentelemetry) for more information.
Value should be given as the dotted path to the function.

///

/// details | `OPENTELEMETRY_VARIABLES_CALLBACK`
    attrs: {id: opentelemetry_variables_callback}

Type: `Callable[[LifecycleHookContext], dict[str, Any]]` | Default: `"undine.integrations.opentelemetry.redacted_variables"`

Function that returns the GraphQL variables that are attached to OpenTelemetry operation spans.
By default, the name of each variable is attached with its value redacted,
since the values can contain sensitive data.
See [OpenTelemetry](integrations.md#opentelemetry) for more information.
Value should be given as the dotted path to the function.

///

/// details | `OPTIMIZER_CLASS`
    attrs: {id: optimizer_class}

Type: `type[QueryOptimizer]` | Default: `"undine.optimizer.optimizer.QueryOptimizer"`

The optimizer class to use for optimizing queries.
Value should be given as the dotted path to the optimizer class.

///

/// details | `ORDER_EXTENSIONS_KEY`
    attrs: {id: order_extensions_key}

Type: `str` | Default: `"undine_order"`

The key used to store an `Order` in the `extensions` of its `GraphQLEnumValue`.

///

/// details | `ORDERSET_EXTENSIONS_KEY`
    attrs: {id: orderset_extensions_key}

Type: `str` | Default: `"undine_orderset"`

The key used to store a `OrderSet` in the `extensions` of its `GraphQLEnumType`.

///

/// details | `PAGINATION_INDEX_KEY`
    attrs: {id: pagination_index_key}

Type: `str` | Default: `"_undine_pagination_index"`

The key to which a nested pagination indexes are annotated to.

///

/// details | `PAGINATION_ORDERING_KEY`
    attrs: {id: pagination_ordering_key}

Type: `str` | Default: `"_undine_pagination_ordering"`

The key prefix to which cursor pagination annotates the ordering values that are not plain columns,
so that they are available for building cursors.

///

/// details | `PAGINATION_PAGE_SIZE`
    attrs: {id: pagination_page_size}

Type: `int` | Default: `100`

The maximum number of items to return from a page when paginating.

///

/// details | `PAGINATION_START_INDEX_KEY`
    attrs: {id: pagination_start_index_key}

Type: `str` | Default: `"_undine_pagination_start"`

The key to which a nested pagination start indexes are annotated to.

///

/// details | `PAGINATION_STOP_INDEX_KEY`
    attrs: {id: pagination_stop_index_key}

Type: `str` | Default: `"_undine_pagination_stop"`

The key to which a nested pagination stop indexes are annotated to.

///

/// details | `PAGINATION_TOTAL_COUNT_KEY`
    attrs: {id: pagination_total_count_key}

Type: `str` | Default: `"_undine_pagination_total_count"`

The key to which a nested pagination total counts are annotated to.

///

/// details | `PARSE_CACHE_MAX_SIZE`
    attrs: {id: parse_cache_max_size}

Type: `int` | Default: `0`

How many parsed documents the `undine.hooks.ParseCacheHook` keeps in the memory of the process.
Set to `0` (default) to disable the cache.
See [document caching](caching.md#document-caching) for more information.

///

/// details | `PERSISTED_DOCUMENTS_ONLY`
    attrs: {id: persisted_documents_only}

Type: `bool` | Default: `False`

Whether to only allow persisted documents to be executed in the GraphQL API.

///

/// details | `PERSISTED_DOCUMENTS_PATH`
    attrs: {id: persisted_documents_path}

Type: `str` | Default: `"persisted-documents/"`

The path where the persisted documents registration endpoint is located by default.

///

/// details | `PERSISTED_DOCUMENTS_PERMISSION_CALLBACK`
    attrs: {id: persisted_documents_permission_callback}

Type: `PersistedDocumentsPermissionsCallback` | Default: `undine.persisted_documents.utils.default_permission_callback`

The function to use for permission checks for registration of persisted documents.

///

/// details | `PERSISTED_DOCUMENTS_VIEW_NAME`
    attrs: {id: persisted_documents_view_name}

Type: `str` | Default: `"persisted_documents"`

The name of given to the persisted documents registration view in the URLconf.

///

/// details | `PG_TEXT_SEARCH_PREFIX`
    attrs: {id: pg_text_search_prefix}

Type: `str` | Default: `"_undine_ts_vector"`

A prefix to use for the filter aliases of postgres full text search `Filters`.

///

/// details | `PREFETCH_HACK_CACHE_KEY`
    attrs: {id: prefetch_hack_cache_key}

Type: `str` | Default: `"_undine_prefetch_hack_cache"`

The key to use for storing the prefetch hack cache in the queryset hints.

///

/// details | `QUERY_TYPE_EXTENSIONS_KEY`
    attrs: {id: query_type_extensions_key}

Type: `str` | Default: `"undine_query_type"`

The key used to store a `QueryType` in the `extensions` of its `GraphQLObjectType`.

///

/// details | `QUERY_TYPE_FILTER_INPUT_KEY`
    attrs: {id: query_type_filter_input_key}

Type: `str` | Default: `"filter"`

The name of the input argument that is created for a `FilterSet` when a `QueryType`
using that `FilterSet` is used in a list `Entrypoint` or many-related `Field`.

///

/// details | `QUERY_TYPE_ORDER_INPUT_KEY`
    attrs: {id: query_type_order_input_key}

Type: `str` | Default: `"orderBy"`

The name of the input argument that is created for an `OrderSet` when a `QueryType`
using that `OrderSet` is used in a list `Entrypoint` or many-related `Field`.

///

/// details | `REQUEST_CACHE_ACTIVE_EXTENSIONS_KEY`
    attrs: {id: request_cache_active_extensions_key}

Type: `str` | Default: `"undine_request_cache_active"`

The key on `schema.extensions` set to `True` when the schema has an `Entrypoint` that can be
cached. Used internally to install the `undine.hooks.RequestCacheHook` only for the schemas
that need it.

///

/// details | `REQUEST_CACHE_ALIAS`
    attrs: {id: request_cache_alias}

Type: `str` | Default: `"default"`

The cache alias to use for caching requests using the `@cache` directive.

///

/// details | `REQUEST_CACHE_EXTRA_CONTEXT`
    attrs: {id: request_cache_extra_context}

Type: `Callable[[LifecycleHookContext], dict[str, Any]]` | Default: `"undine.hooks.default_extra_context"`

Function to use for extra context to add to the cache key.
Value should be given as the dotted paths to the function.

///

/// details | `REQUEST_CACHE_READ_PREDICATE`
    attrs: {id: request_cache_read_predicate}

Type: `Callable[[LifecycleHookContext], bool]` | Default: `"undine.hooks.should_read_from_cache"`

Function to use for checking if the result should be read from cache.
Value should be given as the dotted paths to the function.

///

/// details | `REQUEST_CACHE_WRITE_PREDICATE`
    attrs: {id: request_cache_write_predicate}

Type: `Callable[[LifecycleHookContext], bool]` | Default: `"undine.hooks.should_write_to_cache"`

Function to use for checking if the result should be written to cache.
Value should be given as the dotted paths to the function.

///

/// details | `REQUEST_CACHE_PREFIX`
    attrs: {id: request_cache_prefix}

Type: `str` | Default: `"undine-cache"`

The prefix to use for the cache keys when caching requests using the `@cache` directive.

///

/// details | `RESOLVER_ROOT_PARAM_NAME`
    attrs: {id: resolver_root_param_name}

Type: `str` | Default: `"root"`

The name of the root/parent parameter in `Field`/`Entrypoint` resolvers.

///

/// details | `ROOT_TYPE_EXTENSIONS_KEY`
    attrs: {id: root_type_extensions_key}

Type: `str` | Default: `"undine_root_type"`

The key used to store a `RootType` in the `extensions` of its `GraphQLObjectType`.

///

/// details | `ROOT_VALUE`
    attrs: {id: root_value}

Type: `Any` | Default: `None`

The root value for the GraphQL execution. Can be accessed by `Entrypoint` resolvers
from the `root` argument.

///

/// details | `SCALAR_EXTENSIONS_KEY`
    attrs: {id: scalar_extensions_key}

Type: `str` | Default: `"undine_scalar"`

The key used to store a Undine `ScalarType` in the `extensions` of its `GraphQLScalarType`.

///

/// details | `SCHEMA`
    attrs: {id: schema}

Type: `GraphQLSchema` | Default: `"undine.settings.example_schema"`

The file and variable where the GraphQL Schema for Undine is located.
Value should be given as the dotted path, usually created using `undine.schema.create_schema`.

///

/// details | `SCHEMA_DIRECTIVES_EXTENSIONS_KEY`
    attrs: {id: schema_directives_extensions_key}

Type: `str` | Default: `"undine_schema_directives"`

The key used to store the schema definition directives in the `extensions` of its `GraphQLSchema`.

///

/// details | `SDL_PRINTER`
    attrs: {id: sdl_printer}

Type: `type[SDLPrinter]` | Default: `"undine.utils.graphql.sdl_printer.SDLPrinter"`

The SDL printer to use. Value should be given as the dotted path to the SDL printer class.

///

/// details | `SENTRY_REPORT_ERROR_PREDICATE`
    attrs: {id: sentry_report_error_predicate}

Type: `Callable[[GraphQLError], bool]` | Default: `"undine.integrations.sentry.report_server_errors"`

Function to use for checking if a GraphQL error should be reported to Sentry as an issue.
By default, only errors that indicate a fault in the server are reported.
See [Sentry](integrations.md#sentry) for more information.
Value should be given as the dotted path to the function.

///

/// details | `SENTRY_SKIP_FIELD_SPANS_PREDICATE`
    attrs: {id: sentry_skip_field_spans_predicate}

Type: `Callable[[LifecycleHookContext], bool]` | Default: `"undine.integrations.sentry.skip_introspection_queries"`

Function to use for checking if an operation should be recorded without its field spans.
By default, introspection queries are recorded without them, since they resolve a field for
every type and field in the schema.
See [Sentry](integrations.md#sentry) for more information.
Value should be given as the dotted path to the function.

///

/// details | `SENTRY_SPAN_CALLBACK`
    attrs: {id: sentry_span_callback}

Type: `Callable[[RecordedSpan, LifecycleHookContext], None]` | Default: `"undine.integrations.sentry.no_op_span_callback"`

Function called with each span the Sentry lifecycle hook records so it can add its own
attributes to it. By default, no attributes are added.
See [Sentry](integrations.md#sentry) for more information.
Value should be given as the dotted path to the function.

///

/// details | `SENTRY_VARIABLES_CALLBACK`
    attrs: {id: sentry_variables_callback}

Type: `Callable[[LifecycleHookContext], dict[str, Any]]` | Default: `"undine.integrations.sentry.redacted_variables"`

Function that returns the GraphQL variables that are attached to Sentry operation spans.
By default, the name of each variable is attached with its value redacted,
since the values can contain sensitive data.
See [Sentry](integrations.md#sentry) for more information.
Value should be given as the dotted path to the function.

///

/// details | `SSE_KEEP_ALIVE_INTERVAL`
    attrs: {id: sse_keep_alive_interval}

Type: `int` | Default: `12`

Interval in seconds for SSE keep-alive pings sent on the event stream.
These pings prevent reverse proxies and load balancers from closing idle connections.
Set to `0` to disable.

///

/// details | `SSE_OPERATION_STREAM_OPEN_TIMEOUT`
    attrs: {id: sse_operation_stream_open_timeout}

Type: `int` | Default: `30`

Timeout in seconds for an operation to wait for the event stream to open (Single Connection mode).

///

/// details | `SSE_STREAM_SESSION_PREFIX`
    attrs: {id: sse_stream_session_prefix}

Type: `str` | Default: `"graphql-over-sse-stream"`

Key prefix used to store the GraphQL over SSE stream state in the user's session (Single Connection mode).

///

/// details | `SSE_TOKEN_HEADER_NAME`
    attrs: {id: sse_token_header_name}

Type: `str` | Default: `"X-GraphQL-Event-Stream-Token"`

The name of the HTTP header to use for the GraphQL over SSE event stream token (Single Connection mode).

///

/// details | `SSE_TOKEN_QUERY_PARAM_NAME`
    attrs: {id: sse_token_query_param_name}

Type: `str` | Default: `"token"`

The name of the query string parameter to use for the GraphQL over SSE event stream token (Single Connection mode).

///

/// details | `TESTING_CLIENT_FULL_STACKTRACE`
    attrs: {id: testing_client_full_stacktrace}

Type: `bool` | Default: `False`

Whether to include the full stacktrace in testing client instead of just the relevant frames
when checking where SQL queries are made.

///

/// details | `TESTING_CLIENT_NO_ASYNC_TIMEOUT`
    attrs: {id: testing_client_no_async_timeout}

Type: `bool` | Default: `False`

Whether to disable the websocket timeouts in testing client.
Can be useful in debugging.

///

/// details | `TOTAL_COUNT_PARAM_NAME`
    attrs: {id: total_count_param_name}

Type: `str` | Default: `"totalCount"`

The name of the parameter in a connection `ObjectType` for holding the count for the
total number of items that can be queried from the connection.

///

/// details | `UNDINE_PERSISTED_DOCUMENTS_MODEL`
    attrs: {id: undine_persisted_documents_model}

Type: `type[Model]` | Default: `"undine.persisted_documents.models.PersistedDocument"`

**NOTE**: This setting should be set in the top level of the settings file, not in the `UNDINE` dictionary!

The model to use for the `PersistedDocument` model.
Works similarly to [`AUTH_USER_MODEL`][AUTH_USER_MODEL]{:target="_blank"},
so must be set before running migrations for the persisted documents app.

[AUTH_USER_MODEL]: https://docs.djangoproject.com/en/stable/topics/auth/customizing/#substituting-a-custom-user-model

///

/// details | `UNION_TYPE_EXTENSIONS_KEY`
    attrs: {id: union_type_extensions_key}

Type: `str` | Default: `"undine_union_type"`

The key used to store a Undine `UnionType` in the `extensions` of its `GraphQLUnion`.

///

/// details | `USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1`
    attrs: {id: use_sse_distinct_connections_for_http_1}

Type: `bool` | Default: `False`

Whether Server-Sent Events should use distinct connections mode even with a HTTP/1.1 connection.
Note that when using HTTP/1.1, the maximum number of open connections is limited to 6 per domain
and browser. That means you will likely hit the limit in a real production environment
with multiple requests and browser tabs.

///

/// details | `VALIDATION_CACHE_MAX_SIZE`
    attrs: {id: validation_cache_max_size}

Type: `int` | Default: `0`

How many validated documents the `undine.hooks.ValidationCacheHook` keeps in the memory
of the process. Set to `0` (default) to disable the cache.
See [document caching](caching.md#document-caching) for more information.

///

/// details | `VISIBILITY_ACTIVE_EXTENSIONS_KEY`
    attrs: {id: visibility_active_extensions_key}

Type: `str` | Default: `"undine_visibility_active"`

The key on `schema.extensions` set to `True` when [visibility](visibility.md) is
detected in the schema. Used internally to install the visibility validation
rule per schema; you rarely need to read it yourself.

///

/// details | `VISIBILITY_CACHE_ALIAS`
    attrs: {id: visibility_cache_alias}

Type: `str` | Default: `"default"`

The cache alias to use for visibility caching.

///

/// details | `VISIBILITY_CACHE_EXTRA_CONTEXT`
    attrs: {id: visibility_cache_extra_context}

Type: `Callable[[DjangoRequestProtocol], Any]` | Default: `"undine.utils.visibility.default_visibility_extra_context"`

Function returning any JSON-serialisable extra context added to the cross-request
[visibility cache](caching.md#visibility-caching) key. Use this when
per-user visibility depends on more than the user primary key (for example a
tenant identifier or group membership).

///

/// details | `VISIBILITY_CACHE_PREFIX`
    attrs: {id: visibility_cache_prefix}

Type: `str` | Default: `"undine_visibility"`

Prefix used for the cross-request [visibility cache](caching.md#visibility-caching) keys.

///

/// details | `VISIBILITY_CACHE_TIMEOUT`
    attrs: {id: visibility_cache_timeout}

Type: `int` | Default: `0`

How many seconds to cache the filtered introspection payload per user context.
Set to `0` (default) to disable cross-request caching; the per-request visibility
memoization still runs.

///

/// details | `VISIBILITY_MEMO_ATTRIBUTE`
    attrs: {id: visibility_memo_attribute}

Type: `str` | Default: `"_undine_visibility_memo"`

The attribute on the request where visibility check results are memoized for the duration
of the request. This is separate from the cross-request visibility cache.

///

/// details | `WEBSOCKET_CONNECTION_INIT_HOOK`
    attrs: {id: websocket_connection_init_hook}

Type: `WebSocketConnectionInitHook` | Default: `"undine.utils.graphql.websocket.connection_init_hook"`

The function to use for custom `ConnectionInit` logic.
Value should be given as the dotted path to the function.

///

/// details | `WEBSOCKET_CONNECTION_INIT_TIMEOUT_SECONDS`
    attrs: {id: websocket_connection_init_timeout_seconds}

Type: `int` | Default: `3`

The number of seconds to wait for the `ConnectionInit` message after opening a WebSocket before closing it.

///

/// details | `WEBSOCKET_PATH`
    attrs: {id: websocket_path}

Type: `str` | Default: `"graphql/"`

The path where the GraphQL over WebSocket endpoint is located
if using `undine.integrations.channels.get_websocket_enabled_app`.

///

/// details | `WEBSOCKET_PING_HOOK`
    attrs: {id: websocket_ping_hook}

Type: `WebSocketConnectionPingHook` | Default: `"undine.utils.graphql.websocket.ping_hook"`

The function for specifying custom `Ping` message logic.
Value should be given as the dotted path to the function.

///

/// details | `WEBSOCKET_PONG_HOOK`
    attrs: {id: websocket_pong_hook}

Type: `WebSocketConnectionPongHook` | Default: `"undine.utils.graphql.websocket.pong_hook"`

The function to for specifying custom `Pong` message logic.
Value should be given as the dotted path to the function.

///

---
