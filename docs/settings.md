# Settings

In this section, we'll cover the settings that can be used to customize Undine.
The settings can also be found in the [settings file]{:target="_blank"}.

[settings file]: https://github.com/MrThearMan/undine/blob/main/undine/settings.py

## Required

### `SCHEMA`

Describes the location of the schema to use for the GraphQL API.
Should be given as the dotted path to the schema variable.

### `GRAPHQL_PATH`

The URL path where the GraphQL endpoint is located by default.

## Flags

### `ALLOW_DID_YOU_MEAN_SUGGESTIONS`

Whether to allow the _'did you mean'_ suggestions on error messages.

### `ALLOW_INTROSPECTION_QUERIES`

Whether schema introspection queries are allowed or not. Should set to `True` if you want to use the GraphiQL.

### `CAMEL_CASE_SCHEMA_FIELDS`

Should names be converted from _'snake_case'_ to _'camelCase'_ for the GraphQL schema?

### `FILE_UPLOAD_ENABLED`

Whether file uploads are enabled. Should enable CSRF protection on the GraphiQL endpoint if enabled.

### `MUTATION_FULL_CLEAN`

Whether to run `model.full_clean()` when mutating a model. Turning this off can reduce
the number of database queries during mutations.

### `PERSISTED_DOCUMENTS_ONLY`

Whether to only allow persisted documents to be executed.

## Limits

### `CONNECTION_PAGE_SIZE`

The maximum number of items to return in a page of a Connection.

### `ENTRYPOINT_LIMIT_PER_MODEL`

Default number of objects that are fetched per model when fetching results in an abstract type Entrypoint.

### `MAX_FILTERS_PER_TYPE`

The maximum number of filters allowed for a single `FilterSet`.

### `MAX_ORDERS_PER_TYPE`

The maximum number of orders allowed for a single `OrderSet`.

## GraphQL execution

### `ADDITIONAL_VALIDATION_RULES`

Additional validation rules to use for validating the GraphQL schema.

### `EXECUTION_CONTEXT_CLASS`

GraphQL execution context class used by the schema.

### `MAX_ALLOWED_ALIASES`

The maximum number of aliases allowed in a single operation.

### `MAX_ALLOWED_DIRECTIVES`

The maximum number of directives allowed in a single operation.

### `MAX_ERRORS`

The maximum number of validation errors allowed in a GraphQL request before it is rejected.

### `MAX_QUERY_COMPLEXITY`

Maximum query complexity that is allowed to be queried in a single operation.

### `MAX_TOKENS`

Maximum number of tokens the GraphQL parser will parse before it rejects a request.

### `MIDDLEWARE`

Middleware to use in GraphQL field resolving.

### `MUTATION_INSTANCE_LIMIT`

The maximum number of objects that can be mutated in a single mutation.

### `NO_ERROR_LOCATION`

Whether to add the location information to GraphQL errors.

### `ROOT_VALUE`

The root value for the GraphQL execution.

## Hooks

### `OPERATION_HOOKS`

Hooks to run during the operation.

### `PARSE_HOOKS`

Hooks to run during parsing the GraphQL request.

### `VALIDATION_HOOKS`

Hooks to run during validation the GraphQL request.

### `EXECUTION_HOOKS`

Hooks to run during execution the GraphQL request.

## Testing client

### `TESTING_CLIENT_FULL_STACKTRACE`

Whether to include the full stacktrace in testing client instead of just the relevant frames.

## GraphiQL

### `GRAPHIQL_ENABLED`

Whether to enable GraphiQL. Should also set `ALLOW_INTROSPECTION_QUERIES` to `True`.

### `GRAPHIQL_PLUGIN_EXPLORER_VERSION`

Version of the plugin explorer to use for GraphiQL.

### `GRAPHIQL_REACT_VERSION`

Version of React to use for GraphiQL.

### `GRAPHIQL_VERSION`

Version of GraphiQL to use.

## Django-modeltranslation

### `MODELTRANSLATION_INCLUDE_TRANSLATABLE`

Whether to add translatable fields to the GraphQL schema when using `django-modeltranslation`.

### `MODELTRANSLATION_INCLUDE_TRANSLATIONS`

Whether to add translation fields to the GraphQL schema when using `django-modeltranslation`.

## Optimizer

### `CONNECTION_START_INDEX_KEY`

The key to which the connection's pagination start index is annotated to or added to in the queryset hints.

### `CONNECTION_STOP_INDEX_KEY`

The key to which the connection's pagination stop index is annotated to or added to in the queryset hints.

### `CONNECTION_INDEX_KEY`

The key to which nested connection node's pagination index is annotated to the queryset.

### `CONNECTION_TOTAL_COUNT_KEY`

The key to which the connection's total count annotated to or added to in the queryset hints.

### `DISABLE_ONLY_FIELDS_OPTIMIZATION`

Disable optimizing fetched fields with `queryset.only()`.

### `OPTIMIZER_CLASS`

The optimizer class to use for optimizing queries.

### `PREFETCH_HACK_CACHE_KEY`

The key to use for storing the prefetch hack cache in the queryset hints.

## Argument & parameter names

### `MUTATION_INPUT_DATA_KEY`

The key used for the input argument of a MutationType.

### `QUERY_TYPE_FILTER_INPUT_KEY`

The key used for the filter argument of QueryType.

### `QUERY_TYPE_ORDER_INPUT_KEY`

The key used for the order by argument of a `QueryType`.

### `RESOLVER_ROOT_PARAM_NAME`

The name of the root/parent parameter in resolvers.

### `TOTAL_COUNT_PARAM_NAME`

The name of the total count parameter in connection resolvers.

## Other

### `DOCSTRING_PARSER`

The docstring parser to use.

### `SDL_PRINTER`

The SDL printer to use.

## Extensions keys

### `CALCULATION_ARGUMENT_EXTENSIONS_KEY`

The key used to store a `CalculationArgument` in the `extensions` of the GraphQL type.

### `CONNECTION_EXTENSIONS_KEY`

The key used to store a `Connection` in the `extensions` of the GraphQL type.

### `DIRECTIVE_ARGUMENT_EXTENSIONS_KEY`

The key used to store a `DirectiveArgument` in the `extensions` of the GraphQL type.

### `DIRECTIVE_EXTENSIONS_KEY`

The key used to store a `Directive` in the `extensions` of the GraphQL type.

### `ENTRYPOINT_EXTENSIONS_KEY`

The key used to store an `Entrypoint` in the `extensions` of the GraphQL type.

### `FIELD_EXTENSIONS_KEY`

The key used to store a `Field` in the `extensions` of the GraphQL type.

### `FILTER_EXTENSIONS_KEY`

The key used to store a `Filter` in the `extensions` of the GraphQL type.

### `FILTERSET_EXTENSIONS_KEY`

The key used to store a `FilterSet` in the `extensions` of the GraphQL type.

### `INPUT_EXTENSIONS_KEY`

The key used to store an `Input` in the `extensions` of the GraphQL type.

### `INTERFACE_FIELD_EXTENSIONS_KEY`

The key used to store an `InterfaceField` in the `extensions` of the GraphQL type.

### `INTERFACE_TYPE_EXTENSIONS_KEY`

The key used to store a `InterfaceType` in the `extensions` of the GraphQL type.

### `MUTATION_TYPE_EXTENSIONS_KEY`

The key used to store a `MutationType` in the `extensions` of the GraphQL type.

### `ORDER_EXTENSIONS_KEY`

The key used to store an `Order` in the `extensions` of the GraphQL type.

### `ORDERSET_EXTENSIONS_KEY`

The key used to store a `OrderSet` in the `extensions` of the GraphQL type.

### `QUERY_TYPE_EXTENSIONS_KEY`

The key used to store a `QueryType` in the `extensions` of the GraphQL type.

### `ROOT_TYPE_EXTENSIONS_KEY`

The key used to store a `RootType` in the `extensions` of the GraphQL type.

### `SCALAR_EXTENSIONS_KEY`

The key used to store a `Scalar` in the `extensions` of the GraphQL type.

### `SCHEMA_DIRECTIVES_EXTENSIONS_KEY`

The key used to store the schema directives in the `extensions` of the GraphQL type.

### `UNION_TYPE_EXTENSIONS_KEY`

The key used to store a `UnionType` in the `extensions` of the GraphQL type.  
