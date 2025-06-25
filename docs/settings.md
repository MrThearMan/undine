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

/// details | `ADDITIONAL_VALIDATION_RULES`
    attrs: {id: additional_validation_rules}

Type: `list[type[ASTValidationRule]]` | Default: `[]`

Additional validation rules to use for validating the GraphQL schema.
Values should be given as the dotted paths to the validation rules used.

///

/// details | `ALLOW_DID_YOU_MEAN_SUGGESTIONS`
    attrs: {id: allow_did_you_mean_suggestions}

Type: `bool` | Default: `False`

Whether to allow the _'did you mean'_ suggestions on error messages.

///

/// details | `ALLOW_INTROSPECTION_QUERIES`
    attrs: {id: allow_introspection_queries}

Type `bool` | Default: `False`

Whether schema introspection queries are allowed or not. Should set this to `True`
if using GraphiQL.

///

/// details | `ASYNC`
    attrs: {id: async}

Type `bool` | Default: `False`

Whether to use async view for the GraphQL endpoint or not. Allows using async resolvers
for `Fields` and `Entrypoints`. See [Async Support](async.md) for more information.

///

/// details | `CALCULATION_ARGUMENT_EXTENSIONS_KEY`
    attrs: {id: calculation_argument_extensions_key}

Type: `str` | Default: `"undine_calculation_argument"`

The key used to store a `CalculationArgument` in the `extensions` of the `GraphQLArgument`.

///

/// details | `CAMEL_CASE_SCHEMA_FIELDS`
    attrs: {id: camel_case_schema_fields}

Type: `bool` | Default: `True`

Should names be converted from _'snake_case'_ to _'camelCase'_ for the GraphQL schema?
Conversion is not applied if `schema_name` is set manually.

///

/// details | `CONNECTION_EXTENSIONS_KEY`
    attrs: {id: connection_extensions_key}

Type: `str` | Default: `"undine_connection"`

The key used to store a `Connection` in the `extensions` of the `GraphQLObjectType`.

///

/// details | `CONNECTION_INDEX_KEY`
    attrs: {id: connection_index_key}

Type: `str` | Default: `"_undine_pagination_index"`

The key to which a nested connection's pagination indexes are annotated to.

///

/// details | `CONNECTION_PAGE_SIZE`
    attrs: {id: connection_page_size}

Type: `int` | Default: `100`

The maximum number of items to return from a Connection at a time.

///

/// details | `CONNECTION_START_INDEX_KEY`
    attrs: {id: connection_start_index_key}

Type: `str` | Default: `"_undine_pagination_start"`

The key to which a nested connection's pagination start indexes are annotated to.

///

/// details | `CONNECTION_STOP_INDEX_KEY`
    attrs: {id: connection_stop_index_key}

Type: `str` | Default: `"_undine_pagination_stop"`

The key to which a nested connection's pagination stop indexes are annotated to.

///

/// details | `CONNECTION_TOTAL_COUNT_KEY`
    attrs: {id: connection_total_count_key}

Type: `str` | Default: `"_undine_pagination_total_count"`

The key to which a nested connection's total counts are annotated to.

///

/// details | `DIRECTIVE_ARGUMENT_EXTENSIONS_KEY`
    attrs: {id: directive_argument_extensions_key}

Type: `str` | Default: `"undine_directive_argument"`

The key used to store a `DirectiveArgument` in the `extensions` of the `GraphQLArgument`.

///

/// details | `DIRECTIVE_EXTENSIONS_KEY`
    attrs: {id: directive_extensions_key}

Type `str` | Default: `"undine_directive"`

The key used to store a `Directive` in the `extensions` of the `GraphQLDirective`.

///

/// details | `DISABLE_ONLY_FIELDS_OPTIMIZATION`
    attrs: {id: disable_only_fields_optimization}

Type `bool` | Default: `False`

Disable optimizing fetched fields with `queryset.only()`.

///

/// details | `DOCSTRING_PARSER`
    attrs: {id: docstring_parser}

Type `type[DocstringParserProtocol]` | Default: `"undine.parsers.parse_docstring.RSTDocstringParser"`

The docstring parser to use.
Should be given as the dotted path to the docstring parser class.

///

/// details | `ENTRYPOINT_EXTENSIONS_KEY`
    attrs: {id: entrypoint_extensions_key}

Type `str` | Default: `"undine_entrypoint"`

The key used to store an `Entrypoint` in the `extensions` of the `GraphQLField`.

///

/// details | `ENTRYPOINT_LIMIT_PER_MODEL`
    attrs: {id: entrypoint_limit_per_model}

Type `int` | Default: `100`

Default number of objects that are fetched per model when fetching results in an abstract type
(`UnionType` or `InterfaceType`) `Entrypoint`.

///

/// details | `EXECUTION_CONTEXT_CLASS`
    attrs: {id: execution_context_class}

Type `type[UndineExecutionContext]` | Default: `"undine.execution.UndineExecutionContext"`

GraphQL execution context class used by the schema.
Should be given as the dotted path to the execution context class.

///

/// details | `EXECUTION_HOOKS`
    attrs: {id: execution_hooks}

Type: `list[type[LifecycleHook]]` | Default: `[]`

Hooks to run during execution phase the GraphQL request. See [Lifecycle Hooks](lifecycle-hooks.md) for more information.
Values should be given as the dotted paths to the lifecycle hooks used.

///

/// details | `FIELD_EXTENSIONS_KEY`
    attrs: {id: field_extensions_key}

Type: `str` | Default: `"undine_field"`

The key used to store a `Field` in the `extensions` of the `GraphQLField`.

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

The key used to store a `Filter` in the `extensions` of the `GraphQLInputField`.

///

/// details | `FILTERSET_EXTENSIONS_KEY`
    attrs: {id: filterset_extensions_key}

Type: `str` | Default: `"undine_filterset"`

The key used to store a `FilterSet` in the `extensions` of the `GraphQLInputObjectType`.

///

/// details | `GRAPHIQL_ENABLED`
    attrs: {id: graphiql_enabled}

Type: `bool` | Default: `False`

Whether to enable GraphiQL. Should also set [`ALLOW_INTROSPECTION_QUERIES`](#allow_introspection_queries)
to `True`, so that GraphiQL can introspect the GraphQL schema.

///

/// details | `GRAPHIQL_PLUGIN_EXPLORER_VERSION`
    attrs: {id: graphiql_plugin_explorer_version}

Type: `str` | Default: `"3.2.5"`

Version of the plugin explorer to use for GraphiQL.

///

/// details | `GRAPHIQL_REACT_VERSION`
    attrs: {id: graphiql_react_version}

Type: `str` | Default: `"18.3.1"`

Version of React to use for GraphiQL.

///

/// details | `GRAPHIQL_VERSION`
    attrs: {id: graphiql_version}

Type: `str` | Default: `"3.8.3"`

Version of GraphiQL to use.

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

/// details | `INPUT_EXTENSIONS_KEY`
    attrs: {id: input_extensions_key}

Type: `str` | Default: `"undine_input"`

The key used to store an `Input` in the `extensions` of the `GraphQLInputField`.

///

/// details | `INTERFACE_FIELD_EXTENSIONS_KEY`
    attrs: {id: interface_field_extensions_key}

Type: `str` | Default: `"undine_interface_field"`

The key used to store an `InterfaceField` in the `extensions` of the `GraphQLField`.

///

/// details | `INTERFACE_TYPE_EXTENSIONS_KEY`
    attrs: {id: interface_type_extensions_key}

Type: `str` | Default: `"undine_interface"`

The key used to store a `InterfaceType` in the `extensions` of the `GraphQLInterfaceType`.

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

The maximum number of validation errors allowed in a GraphQL request before it is rejected,
even if validation is still not complete.

///

/// details | `MAX_FILTERS_PER_TYPE`
    attrs: {id: max_filters_per_type}

Type: `int` | Default: `20`

The maximum number of filters allowed to be used for filtering a single `QueryType`.

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

///

/// details | `MAX_TOKENS`
    attrs: {id: max_tokens}

Type `int` | Default: `None`

Maximum number of [GraphQL document tokens]{:target="_blank"} the GraphQL parser will
parse before it rejects a request. By default, this is set to `None` which means no limit.

[GraphQL document tokens]: https://github.com/graphql-python/graphql-core/blob/main/src/graphql/language/token_kind.py

///

/// details | `MIDDLEWARE`
    attrs: {id: middleware}

Type: `list[type[GraphQLFieldResolver]]` | Default: `[]`

Middleware to use during GraphQL field resolving.
See [Custom Middleware]{:target="_blank"} in the GraphQL-core documentation for more information.

[Custom Middleware]: https://graphql-core-3.readthedocs.io/en/latest/diffs.html#custom-middleware

///

/// details | `MODELTRANSLATION_INCLUDE_TRANSLATABLE`
    attrs: {id: modeltranslation_include_translatable}

Type: `bool` | Default: `False`

Whether to add translatable fields to the GraphQL schema when using `django-modeltranslation`.
See [the integration description](integrations.md#django-modeltranslation) for more information.

///

/// details | `MODELTRANSLATION_INCLUDE_TRANSLATIONS`
    attrs: {id: modeltranslation_include_translations}

Type: `bool` | Default: `True`

Whether to add translation fields to the GraphQL schema when using `django-modeltranslation`.
See [the integration description](integrations.md#django-modeltranslation) for more information.

///

/// details | `MUTATION_FULL_CLEAN`
    attrs: {id: mutation_full_clean}

Type: `bool` | Default: `True`

Whether to run `model.full_clean()` when mutating a model. Turning this off can reduce
the number of database queries during mutations, but may introduce issues that would
be solved by running full model validation.

///

/// details | `MUTATION_INSTANCE_LIMIT`
    attrs: {id: mutation_instance_limit}

Type: `int` | Default: `100`

The maximum number of objects that can be mutated in a single mutation.

///

/// details | `MUTATION_INPUT_DATA_KEY`
    attrs: {id: mutation_input_data_key}

Type: `str` | Default: `"input"`

The key that the input argument based on a `MutationType` is added to
when said `MutationType` is used in `Entrypoints`.

///

/// details | `MUTATION_TYPE_EXTENSIONS_KEY`
    attrs: {id: mutation_type_extensions_key}

Type: `str` | Default: `"undine_mutation_type"`

The key used to store a `MutationType` in the `extensions` of the `GraphQLInputObjectType`.

///

/// details | `NO_ERROR_LOCATION`
    attrs: {id: no_error_location}

Type: `bool` | Default: `False`

Whether to remove error location information to GraphQL errors.

///

/// details | `OPERATION_HOOKS`
    attrs: {id: operation_hooks}

Type: `list[type[LifecycleHook]]` | Default: `[]`

Hooks to run encompassing the entire GraphQL operation. See [Lifecycle Hooks](lifecycle-hooks.md) for more information.
Values should be given as the dotted paths to the lifecycle hooks used.

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

The key used to store an `Order` in the `extensions` of the `GraphQLEnumValue`.

///

/// details | `ORDERSET_EXTENSIONS_KEY`
    attrs: {id: orderset_extensions_key}

Type: `str` | Default: `"undine_orderset"`

The key used to store a `OrderSet` in the `extensions` of the `GraphQLEnumType`.

///

/// details | `PARSE_HOOKS`
    attrs: {id: parse_hooks}

Type: `list[type[LifecycleHook]]` | Default: `[]`

Hooks to run during parsing phase of a GraphQL request. See [Lifecycle Hooks](lifecycle-hooks.md) for more information.
Values should be given as the dotted paths to the lifecycle hooks used.

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

Type: `PersistedDocumentsPermissionsCallback` | Default: `None`

The function to use for permission checks for registration of persisted documents.

///

/// details | `PERSISTED_DOCUMENTS_VIEW_NAME`
    attrs: {id: persisted_documents_view_name}

Type: `str` | Default: `"persisted_documents"`

The name of given to the persisted documents registration view in the URLconf.

///

/// details | `PREFETCH_HACK_CACHE_KEY`
    attrs: {id: prefetch_hack_cache_key}

Type: `str` | Default: `"_undine_prefetch_hack_cache"`

The key to use for storing the prefetch hack cache in the queryset hints.

///

/// details | `QUERY_TYPE_EXTENSIONS_KEY`
    attrs: {id: query_type_extensions_key}

Type: `str` | Default: `"undine_query_type"`

The key used to store a `QueryType` in the `extensions` of the `GraphQLObjectType`.

///

/// details | `QUERY_TYPE_FILTER_INPUT_KEY`
    attrs: {id: query_type_filter_input_key}

Type: `str` | Default: `"filter"`

The key that the input argument based on a `FilterSet` of a `QueryType` is added to
when said `QueryType` is used in list `Entrypoints` or "to-many" related `Fields`.

///

/// details | `QUERY_TYPE_ORDER_INPUT_KEY`
    attrs: {id: query_type_order_input_key}

Type: `str` | Default: `"orderBy"`

The key that the input argument based on an `OrderSet` of a `QueryType` is added to
when said `QueryType` is used in list `Entrypoints` or "to-many" related `Fields`.

///

/// details | `RESOLVER_ROOT_PARAM_NAME`
    attrs: {id: resolver_root_param_name}

Type: `str` | Default: `"root"`

The name of the root/parent parameter in `Field`/`Entrypoint` resolvers.

///

/// details | `ROOT_TYPE_EXTENSIONS_KEY`
    attrs: {id: root_type_extensions_key}

Type: `str` | Default: `"undine_root_type"`

The key used to store a `RootType` in the `extensions` of the `GraphQLObjectType`.

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

The key used to store a Undine `ScalarType` in the `extensions` of the `GraphQLScalarType`.

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

The key used to store the schema definition directives in the `extensions` of the `GraphQLSchema`.

///

/// details | `SDL_PRINTER`
    attrs: {id: sdl_printer}

Type: `type[SDLPrinter]` | Default: `"undine.utils.graphql.sdl_printer.SDLPrinter"`

The SDL printer to use. Value should be given as the dotted path to the SDL printer class.

///

/// details | `TESTING_CLIENT_FULL_STACKTRACE`
    attrs: {id: testing_client_full_stacktrace}

Type: `bool` | Default: `False`

Whether to include the full stacktrace in testing client instead of just the relevant frames
when checking where SQL queries are made.

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

The model to use for the `PersistedDocument` model. Works similarly to
[`AUTH_USER_MODEL`](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model){:target="_blank"},
so must be set before running migrations for the persisted documents app.

///

/// details | `UNION_TYPE_EXTENSIONS_KEY`
    attrs: {id: union_type_extensions_key}

Type: `str` | Default: `"undine_union_type"`

The key used to store a Undine `UnionType` in the `extensions` of the `GraphQLUnion`.

///

/// details | `VALIDATION_HOOKS`
    attrs: {id: validation_hooks}

Type: `list[type[LifecycleHook]]` | Default: `[]`

Hooks to run during validation the GraphQL request. See [Lifecycle Hooks](lifecycle-hooks.md) for more information.
Values should be given as the dotted paths to the lifecycle hooks used.

///

---
