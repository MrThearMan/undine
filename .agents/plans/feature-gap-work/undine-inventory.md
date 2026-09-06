# Undine feature inventory

Source: Undine repo at ~/Projects/undine (version 0.5.1 in pyproject.toml).
One line per feature. Names are the real API names.
Items marked "(undocumented)" are in the code but not in docs/ (or only mentioned briefly).

Top-level exports in `undine/__init__.py`: `Calculation`, `CalculationArgument`, `DataLoader`, `Directive`, `DirectiveArgument`, `Entrypoint`, `Field`, `Filter`, `FilterSet`, `GQLInfo`, `Input`, `InterfaceField`, `InterfaceType`, `MutationType`, `Order`, `OrderSet`, `QueryType`, `RootType`, `UnionType`, `create_schema`.

Base requirements: Python >= 3.12, Django >= 5.2.3, graphql-core >= 3.3.0, django-settings-holder, sqlparse.

## 1. Schema, root types and entrypoints

- `RootType` class (`undine.entrypoint`). Defines `Query`, `Mutation`, `Subscription` root object types.
- `Query` root type is required. Each root type needs at least one `Entrypoint`.
- `create_schema(query=..., mutation=..., subscription=..., ...)` (`undine.schema`) builds a `GraphQLSchema`.
- `SCHEMA` setting points to the schema object by dotted path.
- `RootType(schema_name=...)` renames the GraphQL object type.
- `RootType` description from class docstring.
- `RootType(directives=[...])` and decorator syntax for `OBJECT` directives.
- `RootType(extensions={...})`. Root type stored under `ROOT_TYPE_EXTENSIONS_KEY`.
- `Entrypoint` class. A field on a root type. Always needs a reference.
- Function reference: `@Entrypoint` on a method. Return annotation becomes output type. Signature becomes arguments.
- Function entrypoint can return a `TypedDict` for an object with many fields.
- Argument descriptions from reStructuredText docstrings. `DOCSTRING_PARSER` setting for custom parser (`DocstringParserProtocol` in `undine.typing`).
- Method `self` is the resolver root. Name set by `RESOLVER_ROOT_PARAM_NAME` setting. Root value set by `ROOT_VALUE` setting.
- `info: GQLInfo` argument is optional in resolvers.
- `Entrypoint(QueryType)` makes a single-object fetch by `pk` argument.
- `Entrypoint(QueryType, many=True)` makes a list entrypoint. Adds `filter` and `orderBy` args from `FilterSet` and `OrderSet`.
- `Entrypoint(MutationType)` makes a single mutation with `input` argument.
- `Entrypoint(MutationType, many=True)` makes a bulk mutation with a list input.
- `Entrypoint(UnionType)` and `Entrypoint(InterfaceType)` (see sections on unions and interfaces).
- `Entrypoint(Connection(...))` and `Entrypoint(OffsetPagination(...))` for pagination.
- `Entrypoint(nullable=True)`. Entrypoints are non-null by default.
- `Entrypoint(limit=...)` limits list size. Default from `LIST_ENTRYPOINT_LIMIT` setting. Not used for paginated entrypoints.
- `@<entrypoint>.permissions` decorator. Falls back to the QueryType or MutationType permissions.
- `@<entrypoint>.resolve` decorator overrides the resolver. Removes FilterSet and OrderSet args.
- `optimize_sync` and `optimize_async` to optimize a queryset inside a custom resolver.
- `Entrypoint(schema_name=...)`. Field names become camelCase when `CAMEL_CASE_SCHEMA_FIELDS` is on.
- `Entrypoint(description=...)` or class attribute docstring (`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS` setting).
- `Entrypoint(deprecation_reason=...)`.
- `Entrypoint(complexity=...)` adds to the computed complexity. Defaults: QueryType 1, MutationType 1 plus output QueryType, function 0, union or interface 1 per member.
- `Entrypoint(cache_time=..., cache_per_user=...)` response caching.
- `Entrypoint(errors=[ExceptionClass, ...])` errors as data. Makes a union of result and error types.
- `Entrypoint(directives=[...])` or `@` operator (`entrypoint @ Directive(...)`) for `FIELD_DEFINITION` directives.
- `Entrypoint(extensions={...})`. Entrypoint stored under `ENTRYPOINT_EXTENSIONS_KEY`.
- `@<entrypoint>.visible` decorator for visibility (see visibility section).
- Management command `print_schema` prints SDL to stdout. Fails if the schema does not build.
- `print_schema` prints subgraph SDL (as in `_service { sdl }`) for federation schemas.
- `print_schema` ignores visibility. Always prints the full schema.
- `print_schema --check [path]` detects drift against a committed SDL file. Default path `schema.graphql`.
- Management command `check_schema_changes [path]` lists breaking, dangerous and safe changes. Exits non-zero on breaking changes.

## 2. Query types and fields (object types from Django models)

- `QueryType[Model]` class (`undine.query`). Becomes a GraphQL `ObjectType` for a Django model.
- `QueryType(auto=True)` or `AUTOGENERATION` setting. Builds fields from model fields.
- `QueryType(exclude=[...])` excludes model fields from autogeneration.
- `QueryType(filterset=...)` and `QueryType(orderset=...)` attach a `FilterSet` and an `OrderSet`.
- `__filter_queryset__(cls, queryset, info)` classmethod. Always-applied filtering. Also gives default ordering.
- `__get_queryset__(cls, info)` classmethod. Base queryset. Default is the model default manager. (Mentioned briefly in optimizer docs.)
- `__permissions__(cls, instance, info)` classmethod. Runs per returned instance.
- `GraphQLPermissionError` (`undine.exceptions`) for permission failures.
- Pattern: filter out unpermitted rows in `__filter_queryset__` and return null for single items.
- QueryType registry. One registered QueryType per model. Used for relation linking and mutation output types.
- `QueryType(register=False)` to have many QueryTypes per model.
- `__optimize__(cls, data: OptimizationData, info)` classmethod for custom optimizations.
- `QueryType(schema_name=...)`. Description from class docstring.
- `QueryType(cache_time=..., cache_per_user=...)`.
- `QueryType(interfaces=[...])` or decorator syntax to implement interfaces.
- `QueryType(directives=[...])` or decorator syntax. `OBJECT` location.
- `QueryType(extensions={...})`. QueryType stored under `QUERY_TYPE_EXTENSIONS_KEY`.
- `__is_visible__(cls, request)` classmethod for visibility.
- `__is_type_of__` resolves the concrete type for unions and interfaces. Uses exact model class match. (undocumented)
- `str(QueryType)` prints the SDL of the type. Same for most Undine classes (`__str__` uses `SDL_PRINTER`). (undocumented)
- `"field" in QueryType` checks for a field name (`__contains__`). (undocumented)
- `Field` class. One GraphQL field on a QueryType.
- Model field reference: `Field()` with the attribute name, `Field("name")` string, or `Field(Model.field)`.
- String references go through `get_model_field`, which splits on `__`. So lookup paths like `Field("project__name")` likely work. (Not verified by test.)
- Expression reference: `Field(F(...))`, `Field(Count(...))`, `Field(Subquery(...))`. Annotated to the queryset.
- `Field(Q(...))` reference annotates a boolean. (undocumented)
- `Field(lambda: ...)` lazy reference (`LazyLambda`). (undocumented)
- `Field(<GraphQL type>)` uses a raw graphql-core type as the output. (undocumented)
- `Field(str)`, `Field(int)`, `Field(list)`, `Field(dict)`, `Field(SomeEnum)` and other Python type references. (undocumented)
- `Field(SomeQueryType)` explicit related type. `Field(SomeFederationType)` too.
- `Field(Connection(...))` and `Field(OffsetPagination(...))` paginate nested to-many relations.
- `TextChoicesField(choices_enum=...)` (`undine.utils.model_fields`). Django model field that gives one named GraphQL enum per `TextChoices` and returns enum members. (undocumented)
- `CharField(choices=...)` becomes enum `<Model><Field>Choices`. (undocumented)
- `GeneratedField` model fields are supported. (undocumented)
- Function reference: `@Field` on a method. Return type gives output type. Arguments become field arguments. `TypedDict` returns allowed.
- `Calculation[T]` class (`undine.calculation`) with `CalculationArgument` attributes and `__call__(self, info)` returning an ORM expression. Field arguments become annotation inputs.
- Relation fields: `ForeignKey`, `OneToOneField`, `ManyToManyField`, reverse relations link to the registered QueryType.
- Generic relations: `GenericForeignKey` (to union), `GenericRelation`. (Converters exist. Optimizer has `generic_prefetches`.)
- `@<field>.permissions` decorator. Overrides the related QueryType permissions.
- `Field(many=...)` and `Field(nullable=...)`. Auto-detected from the reference.
- `Field(complexity=...)`. Related fields default to 1. Plain fields 0.
- `Field(cache_time=..., cache_per_user=...)`.
- `Field(field_name=...)` maps to a different model field.
- `Field(schema_name=...)`. camelCase via `CAMEL_CASE_SCHEMA_FIELDS`.
- `Field(description=...)`. Defaults to model field `help_text`. Class attribute docstrings with `ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`.
- `Field(deprecation_reason=...)`.
- `@<field>.resolve` decorator for a custom resolver. Root is the model instance.
- `@<field>.optimize` decorator for custom field optimizations.
- `@<field>.visible` decorator for field visibility.
- `Field(errors=[...])` errors as data. Builds `<Type><Field>Value` and error object types in a union. Subclasses also caught.
- Custom error types: exception class static methods `graphql_fields` and `graphql_resolve` add fields to the error object.
- Default error object `GraphQLError { message }`.
- `Field(directives=[...])` or `@` operator. `FIELD_DEFINITION` location.
- `Field(extensions={...})`. Field stored under `FIELD_EXTENSIONS_KEY`.
- Model field type conversion: Django field classes map to GraphQL scalars and enums. Model `choices` become GraphQL enums. (Through `convert_to_graphql_type`.)
- `TextChoices`, `IntegerChoices` and Python `Enum` annotations become GraphQL enums.

## 3. Mutations and inputs

- `MutationType[Model]` class (`undine.mutation`). Becomes a GraphQL `InputObjectType`.
- `MutationType(kind=...)` with kinds `create`, `update`, `delete`, `custom`, `related` (`MutationKind`).
- Kind inferred from class name (`create`, `update`, `delete` in name) or from `__mutate__` / `__bulk_mutate__` (custom).
- `MutationType(auto=True)` autogeneration. Create: non-auto fields with defaults. Update: `pk` plus all fields optional (partial update). Delete: only `pk`.
- `MutationType(exclude=[...])`.
- Output type defaults to the registered QueryType of the same model.
- `__query_type__` classmethod to link a different QueryType.
- `__output_type__` classmethod for a fully custom output type.
- Delete mutations return `<SchemaName>Output { pk }`. (undocumented detail)
- `__permissions__(cls, instance, info, input_data)` classmethod. Runs per mutated instance.
- `__validate__(cls, instance, info, input_data)` classmethod. Raise `GraphQLValidationError`.
- `__after__(cls, instance, info, input_data)` classmethod. Post-mutation side effects.
- `__mutate__(cls, instance, info, input_data)` custom single mutation logic.
- `__bulk_mutate__(cls, instances, info, input_data)` custom bulk mutation logic.
- `custom` kind: no autogeneration, no input-only defaults. Acts as create or update depending on a `pk` input.
- `__filter_queryset__` classmethod on MutationType. Filters the returned queryset. (undocumented)
- `__convert_input__` classmethod. Runs per-input conversion. (undocumented as an override point)
- `__is_visible__` classmethod for visibility.
- Bulk mutations with `Entrypoint(MutationType, many=True)`. Use `bulk_create` internally.
- Nested related mutations with `kind="related"`. Create, update, link, or unlink related objects in one mutation. Works for FK, one-to-one, many-to-many and reverse relations.
- Related existing objects are not fetched for permission checks (performance).
- `MutationType(related_action=...)` with `RelatedAction.null` (default), `RelatedAction.delete`, `RelatedAction.ignore`. Handles unselected reverse relations.
- Many-to-many: unselected through rows are deleted.
- Order of operations: fetch model inputs, add hidden inputs, run function inputs, permissions, validation, remove input-only inputs, mutate, `__after__`.
- Errors from many inputs are collected and returned together. Each error `path` points to the input.
- Mutation runs inside `transaction.atomic`. (undocumented detail)
- `MUTATION_FULL_CLEAN` setting runs `Model.full_clean()` before save. (see settings)
- Model `save` signals (`pre_save`, `post_save`, `m2m_changed`, delete signals) are sent even with bulk operations (`use_save_signals`, `use_delete_signals`). (undocumented)
- Database `IntegrityError` becomes `GraphQLModelConstraintViolationError`. Message comes from the model `Meta.constraints` (`violation_error_message`) for Postgres and SQLite (`undine.utils.constraints.get_constraint_message`). (undocumented)
- `MutationType(schema_name=...)`, docstring description, `directives=[...]` (`INPUT_OBJECT`), `extensions={...}` (`MUTATION_TYPE_EXTENSIONS_KEY`).
- `Input` class. One input field on a MutationType.
- Model field reference: `Input()`, `Input("name")`, `Input(Model.field)`.
- Function reference: `@Input` on a method `(self: instance, info, value)`. Transforms value. Without `value` it becomes hidden.
- Model class reference: `Input(Project)`. Fetches the instance by pk before checks. Errors if not found.
- Python type reference: `Input(bool)` for input-only flags.
- `MutationType` reference in `Input` for related mutations.
- `@<input>.permissions` decorator `(self, info, value)`.
- `@<input>.validate` decorator `(self, info, value)`.
- `@<input>.convert` decorator `(self: Input, value)`. Also runs on defaults.
- `@<input>.visible` decorator.
- `Input(default_value=...)`. Defaults from model `default`. Only for create. Mutable defaults are copied.
- `Input(input_only=True)`. In the schema but removed before save.
- `Input(hidden=True)`. Not in schema. Value added server side (example: current user).
- `Input(required=...)`. Required means non-null in GraphQL.
- `Input(many=...)`, `Input(field_name=...)`, `Input(schema_name=...)`, `Input(description=...)`, `Input(deprecation_reason=...)`.
- `Input(directives=[...])` or `@` operator (`INPUT_FIELD_DEFINITION`). `Input(extensions={...})` (`INPUT_EXTENSIONS_KEY`).
- `MUTATION_INSTANCE_LIMIT` setting. Request-wide cap on mutated instances. Counts bulk items, nested related objects, m2m through rows, deleted or disconnected objects. Error code `MUTATION_TOO_MANY_OBJECTS`.
- `@atomic` operation directive (`AtomicDirective`). Runs all mutations of one operation in one transaction.
- `generate_mutation_input_types` management command. Writes `TypedDict` types `<SchemaName>FullInputData` and `<SchemaName>InputData` to `MUTATION_INPUT_DATA_TYPES_MODULE`.

Not supported:
- `@atomic` is not supported in async mode.
- `required` and nullable cannot be separated for inputs.
- Overriding the resolver of a MutationType entrypoint bypasses the mutation process. Not recommended.

## 4. Filtering

- `FilterSet[Model]` class (`undine.filtering`). Becomes a GraphQL `InputObjectType`.
- Attach with `QueryType(filterset=...)` or decorator syntax `@TaskFilterSet` on the QueryType.
- Adds the `filter` argument to list entrypoints and many-related fields. Name from `QUERY_TYPE_FILTER_INPUT_KEY` setting.
- `FilterSet(auto=True)` or `AUTOGENERATION`. Builds a filter for every model field and every lookup (including transforms like `createdAtYearGte`, `createdAtDateRange`).
- Text fields default to case-insensitive lookups. `nameExact`, `nameStartsWithExact` use case-sensitive lookups.
- `FilterSet(exclude=[...])` excludes fields or specific lookups like `created_at__gte`.
- Logical operators `NOT`, `AND`, `OR`, `XOR` on every FilterSet. Nestable.
- `__filter_queryset__(cls, queryset, info)` on FilterSet. Runs after filters. QueryType version runs before.
- `FilterSet(schema_name=...)`, docstring description, `directives=[...]` (`INPUT_OBJECT`), `extensions={...}` (`FILTERSET_EXTENSIONS_KEY`).
- `FilterSet[ModelA, ModelB]` multi-model FilterSet for unions and interfaces.
- `__is_visible__` on FilterSet.
- `Filter` class. One input field of the FilterSet.
- Model field reference: `Filter()`, `Filter("name")`, `Filter(Model.field)`. Relations and reverse relations allowed.
- Expression reference: `Filter(F(...))`, `Filter(Q(...))`, any `CombinableExpression`, subqueries.
- Function reference: `@Filter` method `(self: Filter, info, *, value)` returning a `Q`.
- Generic relation and `GenericForeignKey` references. (undocumented)
- `Filter(lookup="icontains")`. Default lookup is `exact`.
- `Filter(many=True)` takes a list of values.
- `Filter(match=...)` with `ManyMatch.any` (OR, default), `ManyMatch.all` (AND), `ManyMatch.one_of` (XOR).
- `Filter(distinct=True)` adds `queryset.distinct()` for to-many lookups.
- `Filter(required=True)`. Must be present whenever filtering is used, also inside logical blocks.
- `@<filter>.aliases` decorator returns a dict of expressions to `alias()` on the queryset.
- `Filter(empty_values=[...])`. Global default from `EMPTY_VALUES` setting. Empty values skip the filter.
- `Filter(field_name=...)`, `Filter(schema_name=...)`, `Filter(description=...)`, `Filter(deprecation_reason=...)`.
- Filter permissions: inline checks inside function filters.
- `EmptyFilterResult` exception (`undine.exceptions`) returns an empty queryset instead of an error.
- `Filter(directives=[...])` or `@` operator (`INPUT_FIELD_DEFINITION`). `Filter(extensions={...})` (`FILTER_EXTENSIONS_KEY`).
- `@<filter>.visible` decorator.
- `PostgresFTS(*common_fields, separator="|", **lang_specific_fields)` (`undine.utils.full_text_search`). Filter reference for Postgres full text search. Picks a `SearchVector` per request language. Uses raw `SearchQuery`. Alias prefix from `PG_TEXT_SEARCH_PREFIX` setting. Helpers `TextSearchLang`, `build_pg_search`, `get_request_search_language`. (undocumented, marked no-cover)

Not supported:
- Function filters must name the argument `value` and make it keyword-only.
- Filter permissions have no decorator. Only inline checks in function filters.

## 5. Ordering

- `OrderSet[Model]` class (`undine.ordering`). Becomes a GraphQL `Enum` with `<name>Asc` and `<name>Desc` values.
- Attach with `QueryType(orderset=...)` or decorator syntax.
- Adds `orderBy: [OrderSet!]` argument to list entrypoints and many-related fields. Name from `QUERY_TYPE_ORDER_INPUT_KEY` setting.
- Multi-key ordering: the argument is a list.
- `OrderSet(auto=True)` or `AUTOGENERATION`. `OrderSet(exclude=[...])`.
- `OrderSet(schema_name=...)`, docstring description, `directives=[...]` (`ENUM`), `extensions={...}` (`ORDERSET_EXTENSIONS_KEY`).
- `OrderSet[ModelA, ModelB]` multi-model OrderSet for unions and interfaces.
- `__is_visible__` on OrderSet.
- `Order` class. Model field reference (`Order()`, `Order("name")`, `Order(Model.field)`), `F`, `Q`, expression and subquery references. Relation paths and generic relations allowed.
- `Order(null_placement="first" | "last")`. Default is database default.
- `@<order>.aliases` decorator `(self, info, *, descending)` returns aliases.
- `Order(field_name=...)`, `Order(schema_name=...)` (base name of enum values), `Order(description=...)`, `Order(deprecation_reason=...)`.
- `Order(directives=[...])` or `@` operator (`ENUM_VALUE`). `Order(extensions={...})` (`ORDER_EXTENSIONS_KEY`).
- `@<order>.visible` decorator.
- Default ordering comes from `QueryType.__filter_queryset__`. OrderSet ordering replaces it.

Not supported:
- No function (callable) references for `Order`. Only fields and expressions.

## 6. Pagination and connections

- `OffsetPagination(ref, page_size=..., pagination_handler=OffsetPaginationHandler, description=...)` (`undine.pagination`). Adds `offset` and `limit` args. Returns a plain list.
- `Connection(ref, page_size=..., pagination_handler=CursorPaginationHandler, description=...)` (`undine.relay`). Relay cursor connection with `after`, `before`, `first`, `last`.
- Connection types: `<Type>Connection { totalCount, pageInfo, edges }`, `<Type>Edge { cursor, node }`, shared `PageInfo { hasNextPage, hasPreviousPage, startCursor, endCursor }`.
- Both wrap a `QueryType`, `UnionType`, or `InterfaceType`.
- Both work on entrypoints and on nested many-related `Field`s. Nested pagination is per parent (window functions with partition index).
- Keyset (cursor = row) pagination. Cursor encodes the ordering values. Primary key is always appended to ordering. Stable under inserts and deletes.
- Cursor from a different ordering gives a Bad Request error.
- Union and interface connections: cursor holds shared ordering values, type name, then per-type values.
- Nested connections share one `after` or `before` cursor across all parents.
- `totalCount` for nested connections uses a subquery per parent (can be slow).
- FilterSet and OrderSet args are added next to pagination args.
- `PAGINATION_PAGE_SIZE` setting gives the default page size. `page_size=None` returns everything.
- Custom strategies: subclass `PaginationHandler` (`paginate_queryset`, `paginate_prefetch_queryset`, `optimize`), `CursorPaginationHandler`, or `OffsetPaginationHandler`.
- Argument validation helpers (`undine.relay.validation`, `validate_page_size`, `validate_offset`, `validate_limit`). (undocumented)
- Cursor utils `encode_cursor`, `decode_cursor`, `OrderingDescriptor`, `build_keyset_filter` (`undine.relay.cursors`). (undocumented)
- `CONNECTION_EXTENSIONS_KEY` and `OFFSET_PAGINATION_EXTENSIONS_KEY` settings.

Not supported:
- No page-number pagination class (only offset or cursor).
- No `nodes` shortcut field on connections. Only `edges { node }`.

## 7. Global object IDs (Relay Node)

- `Node` interface (`undine.relay`). Implement with `QueryType(interfaces=[Node])`. Adds `id: ID!`.
- `NodeIDField` interface field. Converts the pk into a global ID. Overrides a model `id` field. Use `pk` to read the raw id.
- `Entrypoint(Node)` creates the `node(id: ID!)` refetch entrypoint.
- `to_global_id(typename, object_id)` and `from_global_id(global_id)` (`undine.relay.node`). Base64 of `ID:<typename>:<id>`.
- `Field(GraphQLID)` auto-resolves a global ID only on Node types. Otherwise it gives the raw pk.

Not supported:
- No plural `nodes(ids: [...])` entrypoint.

## 8. Query optimizer (N+1 and over-fetching)

- Automatic optimizer (`undine.optimizer`). Walks the operation AST at top-level resolvers and builds one optimized queryset.
- Adds `select_related`, `prefetch_related` (`Prefetch` with `to_attr` for aliases and custom schema names), `GenericPrefetch` for generic foreign keys.
- `QuerySet.only()` for selected fields to avoid over-fetching. Disable with `DISABLE_ONLY_FIELDS_OPTIMIZATION` setting.
- Annotations for expression fields and `Calculation` fields.
- Filters, ordering, distinct, pagination applied inside prefetches (nested filtering and pagination are optimized).
- Optimizes through unions, interfaces, fragments, connections (`edges.node`, `totalCount`) and the `Node` interface.
- `optimize_sync(queryset, info, ...)` and `optimize_async(...)` for manual use in custom resolvers.
- `QueryType.__optimize__(data, info)` and `@<field>.optimize` hooks.
- `OptimizationData` (`undine.optimizer.optimizer`) attributes: `model`, `info`, `related_field`, `parent`, `only_fields`, `aliases`, `annotations`, `select_related`, `prefetch_related`, `generic_prefetches`, `filters`, `order_by`, `distinct`, `none`, `pagination`, `queryset_callback`, `pre_filter_callback`, `post_filter_callback`, `field_calculations`.
- `OptimizationData.add_select_related(field_name, query_type=None)`, `add_prefetch_related(field_name, query_type=None, to_attr=None)`, `add_generic_prefetch_related(field_name, related_model, query_type=None, to_attr=None)`.
- `OptimizationResults` and `OptimizationResults.apply(queryset, info)`.
- Automatic promotion of `select_related` to prefetch when annotations, calculations or filter callbacks are needed.
- Documented 14-step order of optimizations.
- Prefetch hack for many-to-many prefetches with pagination or filtering (`undine.optimizer.prefetch_hack`). Uses `PREFETCH_HACK_CACHE_KEY` setting. (undocumented)
- Optimization also runs for mutation output types (`fill_from_mutation_type`). (undocumented)

Not supported:
- Custom resolvers that touch model data must add their own optimizations. The optimizer does not detect it.
- `select_related` promoted to prefetch with filter callbacks can make a non-null field return null.

## 9. DataLoaders

- `DataLoader(load_fn=..., max_batch_size=None, reuse_loads=True, key_hash_fn=..., lock=None)` (`undine.dataloaders`). asyncio batching.
- Needs `ASYNC = True`.
- `DataLoader.load(key)` returns a `Future`. Resolver returns the future without awaiting.
- `DataLoader.load_many(keys)`.
- Load function returns values in key order. Exceptions in the result list become per-key GraphQL errors.
- `max_batch_size` limits keys per batch.
- `reuse_loads` deduplicates the same key in a request (not a cache across requests).
- `prime(key, value, can_prime_pending_loads=False)`, `prime_many(keys, values, ...)`. Values can be exceptions. Shared `asyncio.Lock` for loaders with different keys to the same data.
- `clear(key)`, `clear_many(keys)`, `clear_all()`.
- `key_hash_fn` for non-hashable keys.
- Reused loads are cleared on Django `request_finished` signal.
- Cancels the load task when all waiting futures are canceled.

Not supported:
- No DataLoader support in sync mode.
- No cross-request cache in DataLoader.

## 10. Interfaces

- `InterfaceType` class (`undine.interface`) with `InterfaceField` attributes. Becomes a GraphQL `Interface`.
- Implement with `QueryType(interfaces=[...])` or decorator `@MyInterface` on the QueryType.
- Interfaces can implement other interfaces (`InterfaceType(interfaces=[...])`).
- InterfaceFields are copied as Fields onto implementing QueryTypes. Must match a model field and its output type.
- `InterfaceField(ref, ...)`. `ref` is the GraphQL output type. Optional arguments must match the model field.
- `Entrypoint(InterfaceType, many=True)` returns all implementations. Runs one query per implementation.
- Per-implementation filter and order args: `filter<Model>`, `orderBy<Model>`.
- Shared `InterfaceType(filterset=..., orderset=...)` with multi-model `FilterSet`/`OrderSet`. Filters must reference InterfaceFields.
- Interface entrypoints can be paginated with `Connection` or `OffsetPagination`.
- `InterfaceType(schema_name=..., cache_time=..., cache_per_user=..., directives=[...] (INTERFACE), extensions={...})`. Docstring description. `INTERFACE_TYPE_EXTENSIONS_KEY`.
- `InterfaceField(field_name=..., schema_name=..., description=..., deprecation_reason=..., complexity=..., cache_time=..., cache_per_user=..., directives=[...], extensions={...})`. `INTERFACE_FIELD_EXTENSIONS_KEY`.
- `@<interface_field>.visible` and `InterfaceType.__is_visible__`.
- `Field(InterfaceField)` reference on a QueryType. (undocumented)
- Built-in `Node` interface (see Global object IDs).

Not supported:
- InterfaceFields must map to model fields. No computed (function) interface fields documented.

## 11. Unions

- `UnionType[TypeA, TypeB]` class (`undine.union`). Generic params are QueryTypes. Becomes a GraphQL `Union`.
- `Entrypoint(UnionType, many=True)` returns all instances of all member types. One query per member.
- Per-member filter and order args: `filter<Model>`, `orderBy<Model>`.
- Shared `UnionType(filterset=..., orderset=...)` with multi-model `FilterSet`/`OrderSet` for cross-model filtering and ordering.
- Union entrypoints can be paginated with `Connection` or `OffsetPagination`. Cross-type cursor ordering.
- `UnionType(schema_name=..., cache_time=..., cache_per_user=..., directives=[...] (UNION), extensions={...})`. Docstring description. `UNION_TYPE_EXTENSIONS_KEY`.
- `__resolve_type__` maps model class to member QueryType. (undocumented)
- `__is_visible__` on UnionType.
- `GenericForeignKey` fields become an auto-generated union `<Model><Field>` of all models with a matching `GenericRelation`. (undocumented)
- `GenericForeignKey` mutation input becomes a `@oneOf` input object with one related input per model. (undocumented)

Not supported:
- Union members must be QueryTypes (model-backed). Members are matched by exact model class.

## 12. Directives

- `Directive` class (`undine.directives`). Subclass with `locations=[DirectiveLocation...]`. Metadata only. Behavior must be added (for example with a validation rule).
- Declared directives are added to the schema automatically, even if unused.
- `Directive(register=False)` keeps a directive out of the auto registry. (undocumented)
- All executable locations: `QUERY`, `MUTATION`, `SUBSCRIPTION`, `FIELD`, `FRAGMENT_DEFINITION`, `FRAGMENT_SPREAD`, `INLINE_FRAGMENT`, `VARIABLE_DEFINITION`.
- All type system locations: `SCHEMA` (`create_schema(schema_definition_directives=[...])`), `SCALAR` (`ScalarType`), `OBJECT` (`QueryType`, `RootType`), `FIELD_DEFINITION` (`Field`, `InterfaceField`, `Entrypoint`), `ARGUMENT_DEFINITION` (`CalculationArgument`, `DirectiveArgument`), `INTERFACE`, `UNION`, `ENUM` (`OrderSet`), `ENUM_VALUE` (`Order`), `INPUT_OBJECT` (`MutationType`, `FilterSet`), `INPUT_FIELD_DEFINITION` (`Input`, `Filter`).
- `Directive(is_repeatable=True)`, `Directive(schema_name=...)`, `Directive(extensions={...})` (`DIRECTIVE_EXTENSIONS_KEY`).
- Apply with `directives=[...]` argument, decorator syntax `@MyDirective(...)` on classes, or `field @ MyDirective(...)` matmul.
- `DirectiveArgument(input_type, schema_name=..., description=..., default_value=..., deprecation_reason=..., directives=[...], extensions={...})`. `DIRECTIVE_ARGUMENT_EXTENSIONS_KEY`.
- `__is_visible__` on Directive and `@<arg>.visible` on DirectiveArgument.
- `Directive.__connected__(other)` hook called when the directive is attached to an element. Built-ins use it. (undocumented)
- Built-in `@atomic` (`AtomicDirective`, MUTATION operation). Runs all mutations in one transaction.
- Built-in `@complexity(value: Int!)` (`ComplexityDirective`, FIELD_DEFINITION). Sets field complexity. (undocumented as directive)
- Built-in `@cacheRules(cacheTime: Int!, cachePerUser: Boolean = false)` (`CacheRulesDirective`, FIELD_DEFINITION, OBJECT, INTERFACE, UNION). Same as `cache_time`/`cache_per_user`.
- Built-in `@semanticNonNull(levels: [Int!]! = [0])` (`SemanticNonNullDirective`, FIELD_DEFINITION). Marks a nullable field as null only on error. (undocumented)
- `@oneOf` input objects are printed and introspected (`isOneOf`). Used for GenericForeignKey inputs. (undocumented)
- `@defer` and `@stream` (see incremental delivery).
- `@experimental_disableErrorPropagation` with `EXPERIMENTAL_DISABLE_ERROR_PROPAGATION` setting.
- Federation directives (see federation section).

## 13. Scalars and type conversion

- Built-in GraphQL scalars: `Int`, `Float`, `String`, `Boolean`, `ID`.
- Undine scalars (`undine.scalars`): `Any`, `Base16`, `Base32`, `Base64`, `Date`, `DateTime`, `Decimal`, `Duration` (seconds), `Email`, `File`, `IP`, `IPv4`, `IPv6`, `Image`, `JSON`, `Null`, `Time`, `URL`, `UUID`. Python objects `GraphQLAny`, `GraphQLDateTime`, and so on.
- Scalar `parse` and `serialize` are `singledispatch` functions. Register new input types (example: `whenever` datetimes).
- `ScalarType(name, description=..., specified_by_url=..., directives=[...], extensions={...})` for custom scalars. `SCALAR_EXTENSIONS_KEY`.
- Converters (`undine.converters`) are function dispatchers. Register custom model fields or types for all of Field, Input, Filter, Order (see "Hacking Undine").
- Django model field mapping: `CharField`, `TextField`, `BooleanField`, `IntegerField`, `FloatField`, `DecimalField`, `DateField`, `DateTimeField`, `TimeField`, `DurationField`, `UUIDField`, `EmailField`, `IPAddressField`, `GenericIPAddressField`, `URLField`, `BinaryField`, `JSONField`, `FileField`, `ImageField`, `GeneratedField`, all relation fields, generic relations.
- Python type mapping: `str`, `bool`, `int`, `float`, `Decimal`, `datetime`, `date`, `time`, `timedelta`, `UUID`, `Enum`, `StrEnum`, `IntEnum`, `TextChoices`, `IntegerChoices`, `list`, `dict`, `tuple`, `TypedDict`, `NotRequired`, `Annotated`, async generators and iterables (subscriptions), `asyncio.Future` (DataLoader).
- Enums from Python enums and Django choices become GraphQL enums.
- `TypedDict` as output becomes an object type. As input (function arguments) it becomes an input object `<Name>Input`. (input use undocumented)
- `Annotated[T, Field(...)]` / `Annotated[T, Input(...)]` / `Annotated[T, "description"]` on TypedDict keys sets description, deprecation, default and extensions. (undocumented)
- `NamedTuple` return types become object types (tuple refs). (undocumented)
- Unknown `dict` becomes `JSON`. Unions of several types become `Any`. (undocumented)

## 14. Permissions

- `QueryType.__permissions__(instance, info)` per returned instance.
- `@<field>.permissions` per field `(self: instance, info, value)`. Overrides related QueryType permissions.
- `@<entrypoint>.permissions` per entrypoint `(root, info, value)`. Falls back to QueryType/MutationType permissions.
- `MutationType.__permissions__(instance, info, input_data)` per mutated instance (unsaved instance for create).
- `@<input>.permissions` per input `(self: instance, info, value)`.
- Filter permissions: inline in function filters. `EmptyFilterResult` returns empty results.
- Row-level filtering with `QueryType.__filter_queryset__` (null for single items).
- Subscription permissions (see subscriptions).
- Persisted document registration permission: `PERSISTED_DOCUMENTS_PERMISSION_CALLBACK`.
- Federation entity permissions (see federation).
- Exceptions: `GraphQLPermissionError`, `GraphQLValidationError` and more in `undine.exceptions`. Errors carry `status_code` and `error_code` extensions.
- Errors from many inputs or many instances are returned together with correct `path`.

Not supported:
- No declarative permission classes (like DRF permission classes). Permissions are Python hooks only.
- No built-in Django model permission (`has_perm`) integration.

## 15. Visibility (per-request schema hiding)

- Purpose: hide schema parts per request (feature rollout). Docs say it is not a security boundary.
- Hidden parts are removed from introspection. Using them fails validation with "does not exist" style errors.
- Hooks: `__is_visible__(cls, request)` classmethod on `RootType`, `QueryType`, `MutationType`, `FilterSet`, `OrderSet`, `InterfaceType`, `UnionType`, `Directive`, `FederationType`.
- Hooks: `@<member>.visible` decorator `(self, request)` on `Entrypoint`, `Field`, `Input`, `Filter`, `Order`, `InterfaceField`, `DirectiveArgument`, `CalculationArgument`, `FederationField`.
- Cascading rules: hiding a type hides fields, entrypoints, mutations, union members, interface inheritance, unused filtersets and ordersets.
- Unions collapse when all members are hidden.
- `VisibilityRule` validation rule installed automatically when visibility is used.
- "Did you mean" suggestions are forced off when visibility is used.
- Per-request memo (`VISIBILITY_MEMO_ATTRIBUTE`). Cross-request introspection cache: `VISIBILITY_CACHE_TIMEOUT`, `VISIBILITY_CACHE_ALIAS`, `VISIBILITY_CACHE_PREFIX`, `VISIBILITY_CACHE_EXTRA_CONTEXT`.
- Visibility forces response caching per user.
- Federation: `_entities` honors visibility. `_service { sdl }` and `print_schema` do not.

Not supported:
- Visibility hooks must be sync.
- A hook that raises hides the entity (fail-closed).
- Not applied to exported SDL.

## 16. Validation rules and operation limits

- graphql-core spec rules (`specified_rules`) always run.
- `MaxAliasCountRule` with `MAX_ALLOWED_ALIASES`.
- `MaxDirectiveCountRule` with `MAX_ALLOWED_DIRECTIVES`.
- `MaxComplexityRule` with `MAX_QUERY_COMPLEXITY`. Complexity counts database queries (Entrypoint, Field, InterfaceField `complexity`, `@complexity`).
- `MaxListNestingDepthRule` with `MAX_LIST_NESTING_DEPTH`. Counts nested to-many relations per selection path.
- `VisibilityRule` (auto).
- `NoSchemaIntrospectionCustomRule` when `ALLOW_INTROSPECTION_QUERIES` is false (default false).
- `ADDITIONAL_VALIDATION_RULES` setting for custom `graphql.validation.ValidationRule` classes.
- `MAX_ERRORS` stops validation after N errors.
- `MAX_TOKENS` parser token limit.
- `MAX_FILTERS_PER_TYPE` and `MAX_ORDERS_PER_TYPE` limit filters and orderings per QueryType (default 20 and 10).
- `LIST_ENTRYPOINT_LIMIT` caps list entrypoint results.
- `MUTATION_INSTANCE_LIMIT` caps mutated rows per request.
- `EXECUTION_TIMEOUT_SECONDS` aborts long async operations with `EXECUTION_TIMEOUT` error.
- `ALLOW_DID_YOU_MEAN_SUGGESTIONS` off by default.
- `get_validation_rules(inside_request=...)` (`undine.utils.graphql.validation_rules`). (undocumented)

Not supported:
- No depth limit rule other than list nesting depth. (No plain query depth rule.)
- `EXECUTION_TIMEOUT_SECONDS` does not work in sync mode or for subscriptions.

## 17. Subscriptions

- Needs `ASYNC = True`. Subscription resolvers are always async.
- `Subscription` root type: `create_schema(subscription=...)`.
- AsyncGenerator entrypoint: `@Entrypoint async def countdown(root, info, start: int = 10) -> AsyncGenerator[int, None]`. Output type from the first generic parameter.
- AsyncIterable entrypoint: function returns an `AsyncIterable`.
- Raising an exception closes the subscription with an error. `GraphQLErrorGroup` raises many errors.
- Yielding a `GraphQLError` sends an error and keeps the subscription open.
- `ModelCreateSubscription(QueryType)`, `ModelUpdateSubscription`, `ModelDeleteSubscription`, `ModelSaveSubscription` (`undine.subscriptions`). Django model signal subscriptions. Results go through the QueryType and the optimizer.
- Delete subscriptions get a copy of the instance's own columns. No relations.
- Signal subscription options: `dispatch_uid`, `description`, `timeout` (time between events), `max_backlog` (default 100, 0 for unbounded). Overflow ends the subscription with an error.
- Custom signals: subclass `SignalSubscription` (`signal`, `serialize`, `transform`, `filter`, `topic`) or `QueryTypeSignalSubscription`. Register converters.
- Brokers: `SubscriptionBroker` base, `InMemorySubscriptionBroker` (default, single process), `ChannelLayerSubscriptionBroker` (`undine.integrations.channels`, multi-process with channel layers). Set with `SUBSCRIPTION_BROKER_CLASS`.
- Delivery is at-most-once fan-out. No event storage or replay.
- Entrypoint permissions run per yielded value. Raising closes the subscription.
- WebSocket connection auth via `WEBSOCKET_CONNECTION_INIT_HOOK`.
- Transports: WebSocket (graphql-transport-ws protocol), SSE distinct connections, SSE single connection, multipart/mixed HTTP (Apollo Router protocol). See transports section.

Not supported:
- No sync subscriptions.
- No guaranteed delivery, no missed-event replay on reconnect.

## 18. Incremental delivery (@defer and @stream)

- `@defer` on fragment spreads and inline fragments. `@stream` on list fields.
- Needs `EXPERIMENTAL_INCREMENTAL_DELIVERY = True` and `ASYNC = True`.
- Delivered over HTTP `multipart/mixed; boundary=graphql` (incremental delivery over HTTP RFC). Only this transport in the view code.
- `INCREMENTAL_DELIVERY_EARLY_EXECUTION` lets deferred work start before the initial payload is done.
- `INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL` heartbeats (off by default).
- `EXECUTION_TIMEOUT_SECONDS` also covers subsequent payloads.

Not supported:
- Experimental. Based on draft RFCs and graphql-core experimental API.
- No incremental delivery in sync mode.
- No `@defer`/`@stream` over SSE or WebSocket (view code routes only multipart/mixed to incremental execution).
- No incremental delivery for subscriptions.

## 19. Caching

- Response caching per Query entrypoint: `Entrypoint(cache_time=..., cache_per_user=...)`. Stored in Django cache `REQUEST_CACHE_ALIAS`, key prefix `REQUEST_CACHE_PREFIX`.
- `ENTRYPOINT_DEFAULT_CACHE_TIME` caches every Query entrypoint by default. `cache_time=0` opts out.
- Anonymous and authenticated users always cached apart. `cache_per_user` adds the user pk.
- Cache rules on `Field`, `QueryType`, `InterfaceType`, `InterfaceField`, `UnionType`. Most restrictive rule in the operation wins. Field inherits the rule of its referenced type.
- `@cacheRules` directive does the same in directive form.
- Cache key: document, variables, operation name, operation extensions, auth status, optional user pk.
- `REQUEST_CACHE_EXTRA_CONTEXT` adds custom data (for example language) to the key.
- `REQUEST_CACHE_READ_PREDICATE` and `REQUEST_CACHE_WRITE_PREDICATE` control read and write.
- Only error-free responses are cached.
- Sends `Cache-Control` and `Age` headers for browser and CDN caching.
- Implemented as lifecycle hook `undine.hooks.RequestCacheHook`. Installed only when needed (`REQUEST_CACHE_ACTIVE_EXTENSIONS_KEY`).
- Visibility caching: per-user introspection cache (`VISIBILITY_CACHE_*`). Visibility forces per-user response caching.
- Document caching: `undine.hooks.ParseCacheHook` (`PARSE_CACHE_MAX_SIZE`) and `undine.hooks.ValidationCacheHook` (`VALIDATION_CACHE_MAX_SIZE`). In-process LRU (`undine.utils.lru_cache`).
- Validation cache skipped when visibility is used.

Not supported:
- No response caching with incremental delivery.
- No caching of mutation or subscription results.
- No partial (per-field) result caching. The whole operation response is cached.
- No automatic cache invalidation on model changes. Time-based only.
- No shared (cross-process) document cache. On purpose.

## 20. File upload

- GraphQL multipart request spec (`operations`, `map`, files) parsed by the GraphQL view.
- `FILE_UPLOAD_ENABLED` setting. Off by default. Needs CSRF protection on the endpoint.
- `File` scalar (`FileField`) and `Image` scalar (`ImageField`, needs `undine[image]` / Pillow).
- Files are slotted into variables before execution. Works with MutationType inputs.
- `undine.http.files` helpers. (undocumented)

Not supported:
- No streaming or chunked uploads. No presigned-URL flow.

## 21. Persisted documents and APQ

- Django app `undine.persisted_documents` with model `PersistedDocument` (swappable base `PersistedDocumentBase`).
- `UNDINE_PERSISTED_DOCUMENTS_MODEL` top-level setting to swap the model (like `AUTH_USER_MODEL`).
- Registration view `PersistedDocumentsView` (`undine.persisted_documents.urls`). Path `PERSISTED_DOCUMENTS_PATH`, name `PERSISTED_DOCUMENTS_VIEW_NAME`. Accepts `{"documents": {key: source}}` and returns `sha256:` document IDs.
- Execute with `documentId` instead of `query` on the normal GraphQL endpoint (GraphQL over HTTP persisted documents appendix).
- Document IDs are sha256 of the exact source text (whitespace matters).
- `PERSISTED_DOCUMENTS_PERMISSION_CALLBACK(request, document_map)` protects registration.
- `PERSISTED_DOCUMENTS_ONLY` allow-list mode. Only persisted documents can run.
- `AUTOMATIC_PERSISTED_QUERIES` enables Apollo APQ protocol (`extensions.persistedQuery.sha256Hash`). Hook `undine.hooks.AutomaticPersistedQueriesHook`. Error code `PERSISTED_QUERY_NOT_SUPPORTED` when app is not installed.
- APQ over GET for browser and CDN caching.
- Django admin for persisted documents. Read-only (no add, change or delete). (undocumented)

## 22. Lifecycle hooks (middleware / extensions)

- `LifecycleHook` base class (`undine.hooks`). Context-manager style hooks.
- Hook points: `on_operation` / `on_operation_async`, `on_parse` / `on_parse_async`, `on_validation` / `on_validation_async`, `on_execution` / `on_execution_async`, and `resolve` (per-field graphql-core middleware).
- Register with `ADDITIONAL_LIFECYCLE_HOOKS` (dotted paths).
- `priority` class attribute. `HookPriority` enum: `TRACING` 100, `PARSE_CACHE` 200, `VALIDATION_CACHE` 300, `RESPONSE_CACHE` 400, `VISIBILITY_CACHE` 500, `ATOMIC_MUTATION` 600, `PERSISTED_QUERIES` 700, `DEFAULT` 1000.
- `LifecycleHookContext` fields: `source`, `document`, `validation_errors`, `variables`, `operation_name`, `extensions`, `request`, `result`, `lifecycle_hooks`.
- Setting `context.result` exits early (short-circuit). Adding `validation_errors` skips validation.
- Built-in hooks: `AtomicMutationHook`, `RequestCacheHook`, `VisibilityCacheHook`, `AutomaticPersistedQueriesHook`, `ParseCacheHook`, `ValidationCacheHook`. Tracing hooks in integrations.
- Hooks can add response `extensions` by editing the result. (Docs examples show timing.)

## 23. Apollo Federation 2

- `create_federation_schema(...)` (`undine.federation`). Same as `create_schema` plus `@link`, `Query._service`, `Query._entities`, `_Any`, `_Entity`, `_Service`.
- `FEDERATION_VERSION` setting. Supports `"2.0"` to `"2.15"`. Directives check a minimum version.
- `@link` auto-generated from directives in use (`LinkDirective`, args `url`, `import`, `as`, `for`).
- Directive classes (`undine.federation`): `KeyDirective(fields=..., resolvable=...)`, `ShareableDirective`, `ExternalDirective`, `RequiresDirective`, `ProvidesDirective`, `OverrideDirective(from_=..., label=...)` (progressive override, 2.7+), `InaccessibleDirective`, `TagDirective` (repeatable), `ComposeDirectiveDirective` (2.1+), `InterfaceObjectDirective` (2.3+), `AuthenticatedDirective` (2.5+), `RequiresScopesDirective` (2.5+), `PolicyDirective` (2.6+), `ContextDirective` (2.8+), `FromContextDirective` (2.8+), `CostDirective` (2.9+), `ListSizeDirective(assumed_size, slicing_arguments, sized_fields)` (2.9+), `CacheTagDirective` (2.12+).
- Entities: QueryTypes with `@key`. `_entities` resolves representations.
- Default reference resolver for a single simple key. Custom `__resolve_reference__` on the QueryType for compound or other keys. Returning `None` gives null.
- `FederationType` (`undine.federation`). Entity owned by another subgraph, not backed by a model.
- `FederationField`. Resolves by explicit resolver (`@<field>.resolve` or `@FederationField`), key membership, or `@external`. Otherwise schema build error.
- Stub references: `@key(resolvable=False)` type. Return a representation dict from a resolver.
- Entity permissions: `__permissions__` on QueryType and FederationType run for `_entities`. `@<federation_field>.permissions`. Hooks can be async. Failure nulls only that slot.
- Visibility on `FederationType` and `FederationField`. `_entities` honors visibility.
- `print_schema` and `_service { sdl }` print subgraph SDL.
- `FederatedTracingHook` (`undine.federation.tracing`). Apollo `ftv1` protocol. Triggered by header `apollo-federation-include-trace: ftv1`. Needs `undine[federation-tracing]` (protobuf).
- Verified against Apollo subgraph compatibility harness. Reference `products` subgraph in `tests/test_federation/compatibility/`.
- Federation validation helpers in `undine.federation.validation` (key fields exist, one resolvable key, `@requires` fields). (undocumented)

Not supported:
- Default reference resolver supports only one resolvable `@key` with one unaliased field.
- Federation 1 is not supported (Federation 2 only).
- `_service { sdl }` ignores visibility.

## 24. Integrations

- Channels (`undine[channels]`, `undine.integrations.channels`): `get_websocket_enabled_app(asgi_app)`, `get_sse_enabled_app(asgi_app)`, `get_websocket_and_sse_enabled_app(asgi_app)` for `asgi.py`. Consumers `GraphQLWebSocketConsumer`, SSE single connection consumers and routers. `ChannelLayerSubscriptionBroker`.
- GraphiQL (`undine.integrations.graphiql`): built in, served on GET with `text/html` at the GraphQL endpoint. `GRAPHIQL_ENABLED`. Explorer and history plugins. URL encodes document, variables, headers (shareable). Subscriptions over WebSocket or SSE (`GRAPHIQL_SSE_ENABLED`, `GRAPHIQL_SSE_SINGLE_CONNECTION`). Uses an import map for JS modules.
- Django Debug Toolbar (`undine[debug]`, `undine.integrations.debug_toolbar`): auto-patched. Toolbar data works with GraphiQL and JSON responses.
- django-modeltranslation (`undine.integrations.modeltranslation`): autogeneration includes translation fields and/or translatable fields. `MODELTRANSLATION_INCLUDE_TRANSLATABLE`, `MODELTRANSLATION_INCLUDE_TRANSLATIONS`.
- OpenTelemetry (`undine[opentelemetry]`, `undine.integrations.opentelemetry`): `OpenTelemetryHook` (operation, parse, validate, execute spans) and `OpenTelemetryFullHook` (plus field spans). GraphQL semconv attributes. Subscription spans per result. Redacted document and variables. `OPENTELEMETRY_SKIP_FIELD_SPANS_PREDICATE`, `OPENTELEMETRY_VARIABLES_CALLBACK`, `OPENTELEMETRY_SPAN_CALLBACK`. Helpers `never_skip_field_spans`, `no_traced_variables`.
- Datadog (`undine[datadog]`, `undine.integrations.datadog`): `DatadogHook`, `DatadogFullHook`. Resource `<operation>:<hash>`. `DATADOG_SERVICE_NAME`, `DATADOG_SKIP_FIELD_SPANS_PREDICATE`, `DATADOG_VARIABLES_CALLBACK`, `DATADOG_SPAN_CALLBACK`.
- Sentry (`undine[sentry]`, `undine.integrations.sentry`): `SentryHook`, `SentryFullHook`. Starts transactions for WebSocket and SSE. Names transactions after operations. Reports server-fault errors as issues with GraphQL context. Supports span streaming mode. `RecordedSpan` callback object. `SENTRY_REPORT_ERROR_PREDICATE` (`report_all_errors` helper), `SENTRY_SKIP_FIELD_SPANS_PREDICATE`, `SENTRY_VARIABLES_CALLBACK`, `SENTRY_SPAN_CALLBACK`. Respects `send_default_pii`.
- Apollo federated tracing: `FederatedTracingHook` (`undine[federation-tracing]`).
- Document redaction utility for tracing (`undine.utils.graphql.redaction`). (undocumented as public API)
- Pillow for `Image` scalar (`undine[image]`).
- Postgres full text search filter `PostgresFTS` (django.contrib.postgres). (undocumented)

Not supported:
- No Prometheus or StatsD metrics integration.
- No built-in Apollo Studio usage reporting (only ftv1 traces for federation).
- No DRF serializer or Django forms integration for mutations.
- No django-filter integration (Undine has its own FilterSet).

## 25. Tooling, typing and testing

- Mypy plugin `mypy_undine` (entry point). Checks generic model params, class kwargs, field kwargs, decorator method signatures, resolver return types, FilterSet/OrderSet/Interface model compatibility, directive locations and repeatability. Types `self` as the model. Synthesizes `Directive.__init__` and `FederationType.__init__`.
- Ships `py.typed` (typed package). `GQLInfo` type for `info`. `undine.typing` protocols (`DjangoRequestProtocol`, `DocstringParserProtocol`, and more).
- Pytest plugin `pytest_undine` (entry point `pytest11`). Fixtures `graphql` (`GraphQLClient`), `graphql_async` (`AsyncGraphQLClient`), `undine_settings`.
- `GraphQLClient(document, variables=..., headers=..., operation_name=..., extensions=..., use_persisted_document=False, count_queries=False)`. Auto multipart request when variables contain files.
- Client helpers: `login_with_superuser`, `login_with_regular_user`, `over_websocket`, `websocket()` (`TestWebSocket`), async `over_sse`, `multipart_mixed_subscription`, `incremental_delivery`.
- Response object `GraphQLClientResponse`: `json`, `data`, `results`, `edges`, `node(i)`, `has_errors`, `errors`, `error_message(selector)`, `queries`, `query_count`, `query_log`, `assert_query_count(n)`, `status_code`.
- SQL query capture with stack info (`pytest_undine.query_logging.capture_database_queries`). `TESTING_CLIENT_FULL_STACKTRACE`, `TESTING_CLIENT_NO_ASYNC_TIMEOUT`.
- Management commands: `print_schema` (with `--check`), `check_schema_changes`, `generate_mutation_input_types`.
- `str()` on Undine classes prints SDL. `SDL_PRINTER` setting for a custom printer (`undine.utils.graphql.sdl_printer`).
- Schema sorting and validation on build (`create_schema` raises `UndineErrorGroup` with all schema errors).
- Logging to the `undine` logger (`undine.utils.logging`).
- Docs for LLMs at `https://undine-graphql.dev/llms.txt` (pyproject URL).
- Example project in `example_project/`.

Not supported:
- No client code generation (no typed client SDK generator). Only server-side `TypedDict` generation for mutation input.

## 26. Transports and HTTP

- Django views `graphql_view_sync` and `graphql_view_async` (`undine.http.views`). Pick by `ASYNC`.
- `path("", include("undine.http.urls"))`. Path `GRAPHQL_PATH`, name `GRAPHQL_VIEW_NAME`.
- GraphQL over HTTP: GET and POST. Response types `application/graphql-response+json` and `application/json`. Accept-header content negotiation with quality values.
- Request bodies: `application/json`, `application/graphql`, `application/x-www-form-urlencoded`, `multipart/form-data` (file uploads). GET query params.
- Mutations only over POST (error for GET).
- Subscriptions not allowed over plain HTTP JSON. Must use a streaming transport.
- Persisted documents: `documentId` param. APQ via `extensions`.
- WebSocket: `graphql-transport-ws` protocol via channels. `WEBSOCKET_PATH`, `WEBSOCKET_CONNECTION_INIT_HOOK`, `WEBSOCKET_CONNECTION_INIT_TIMEOUT_SECONDS`, `WEBSOCKET_PING_HOOK`, `WEBSOCKET_PONG_HOOK`. Queries and mutations over WebSocket are toggleable (`ALLOW_QUERIES_WITH_WEBSOCKETS`, `ALLOW_MUTATIONS_WITH_WEBSOCKETS`).
- SSE distinct connections mode (`text/event-stream`, no channels). Blocked on HTTP/1.1 unless `USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1`.
- SSE single connection mode via channels. State in Django sessions, cache and channel layers. Works across workers. Allows replacing a stale stream. Needs authentication. Settings `SSE_STREAM_SESSION_PREFIX`, `SSE_TOKEN_HEADER_NAME`, `SSE_TOKEN_QUERY_PARAM_NAME`, `SSE_OPERATION_STREAM_OPEN_TIMEOUT`.
- `SSE_KEEP_ALIVE_INTERVAL` keep-alive pings.
- Queries and mutations over SSE are toggleable (`ALLOW_QUERIES_WITH_SSE`, `ALLOW_MUTATIONS_WITH_SSE`).
- Multipart HTTP subscriptions (`multipart/mixed; boundary=graphql; subscriptionSpec=1.0`, Apollo Router protocol). `MULTIPART_MIXED_HEARTBEAT_INTERVAL`. `ALLOW_QUERIES_WITH_MULTIPART_MIXED`, `ALLOW_MUTATIONS_WITH_MULTIPART_MIXED`.
- Incremental delivery over `multipart/mixed; boundary=graphql`.
- Streaming responses use `StreamingHttpResponse` with proper no-buffering headers.
- GraphiQL served on GET with `Accept: text/html`.
- HTTP error responses for unsupported method, unsupported content type, SSE not allowed (`undine.http.responses`).

Not supported:
- No query batching (no array of operations in one HTTP request).
- No legacy `subscriptions-transport-ws` (`graphql-ws` subprotocol). Only `graphql-transport-ws`.
- WebSocket and SSE single connection need the channels integration.

## 27. Errors and error handling

- `undine.exceptions` has about 200 error classes. `GraphQLStatusError` base adds `status_code` and `error_code` extensions.
- Common errors: `GraphQLPermissionError`, `GraphQLValidationError`, `GraphQLModelConstraintViolationError`, `GraphQLModelNotFoundError`, `GraphQLErrorGroup` (many errors at once), `EmptyFilterResult`.
- Errors as data: `Field(errors=[...])` and `Entrypoint(errors=[...])` build result unions. Custom error type fields via `graphql_fields` and `graphql_resolve` static methods on the exception.
- Error masking: `ERROR_MASKING_PREDICATE` (default masks unexpected non-GraphQLError exceptions) and `ERROR_MASKING_MESSAGE`. `never_mask_error` to disable. Masked errors keep `path`, `locations`, `status_code`. Originals logged to `undine` logger.
- `INCLUDE_ERROR_TRACEBACK` adds tracebacks (not for masked errors).
- `NO_ERROR_LOCATION` removes `locations` from errors.
- `ALLOW_DID_YOU_MEAN_SUGGESTIONS` off by default.
- `@semanticNonNull` directive and `EXPERIMENTAL_DISABLE_ERROR_PROPAGATION` (`@experimental_disableErrorPropagation`) for null handling.
- Mutation and input errors are aggregated with per-input `path`.
- DataLoader per-key errors.
- Subscriptions: yield `GraphQLError` to send an error without closing.
- Database `IntegrityError` to readable constraint message. (undocumented)

## 28. Async

- `ASYNC = True` switches to the async view. Needs an ASGI server.
- Async resolvers for entrypoints, fields, and parts of QueryType and MutationType hooks.
- Built-in resolvers adapt to async automatically.
- Request user fetched eagerly in async mode.
- Required for DataLoaders, subscriptions, incremental delivery, channels, `EXECUTION_TIMEOUT_SECONDS`.
- `optimize_async` for manual optimization.
- Async federation permission hooks.

Not supported:
- Async resolvers in sync mode raise an error.
- `@atomic` does not work in async mode.
- Visibility hooks must be sync.

## 29. Schema building conventions and naming

- Django app `undine` in `INSTALLED_APPS`. Needs `django.contrib.contenttypes`.
- Settings in a `UNDINE` dict (`undine.settings.undine_settings`, built on django-settings-holder).
- `CAMEL_CASE_SCHEMA_FIELDS` converts snake_case to camelCase. Manual `schema_name` is not converted.
- Descriptions from docstrings, model `help_text`, function docstrings, class attribute docstrings (`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`), reStructuredText `:param:` lines for arguments (`DOCSTRING_PARSER`).
- Class attribute names that clash with Python keywords use `schema_name`.
- All framework hooks use dunder names (`__permissions__`, `__filter_queryset__`, ...) to avoid clashes with field names. (FAQ)
- Decorator syntax to attach FilterSet, OrderSet, interfaces, directives to classes.
- `extensions={...}` on every element. Each element is stored in its GraphQL object extensions under a `*_EXTENSIONS_KEY` setting. Helpers `get_undine_query_type`, `get_undine_field`, `get_undine_entrypoint` and so on (`undine.utils.graphql.undine_extensions`). (helpers undocumented)
- `ROOT_VALUE` and `RESOLVER_ROOT_PARAM_NAME` settings.
- `MUTATION_INPUT_DATA_KEY` (name of `input` argument), `QUERY_TYPE_FILTER_INPUT_KEY` (`filter`), `QUERY_TYPE_ORDER_INPUT_KEY` (`orderBy`), `TOTAL_COUNT_PARAM_NAME` (`totalCount`).
- Schema types are sorted and validated at build. Missing interface implementations are added automatically.
- Type registry deduplicates GraphQL types by name and errors on conflicting definitions (`undine.utils.graphql.type_registry`). (undocumented)
- Custom introspection resolvers honor visibility (`undine.utils.graphql.introspection`). Supports `isOneOf` and `specifiedByURL`. (undocumented)
- Foreign key id selection (for example `projectId` matching `project_id` attname) is read without a join. (undocumented)
- `EXPERIMENTAL_FRAGMENT_ARGUMENTS` enables fragment variables syntax (graphql-core experimental). The optimizer handles fragment variables.

## 30. Extensibility (converters and pluggable classes)

- Converters are function dispatchers (`undine.utils.function_dispatcher.FunctionDispatcher`, own version of `singledispatch`). Register with `@converter.register`.
- Converters: `convert_to_graphql_type`, `convert_to_graphql_argument_map`, `convert_lookup_to_graphql_type`, `convert_model_field_to_python_type`, `convert_graphql_type_to_python_type`, `convert_to_entrypoint_ref`, `convert_to_field_ref`, `convert_to_input_ref`, `convert_to_order_ref`, `convert_to_filter_ref`, `convert_to_federation_field_ref`, `convert_to_field_resolver`, `convert_to_entrypoint_resolver`, `convert_to_filter_resolver`, `convert_to_federation_field_resolver`, `convert_to_entrypoint_subscription`, `convert_to_description`, `convert_to_default_value`, `convert_to_bad_lookups`, `convert_to_entrypoint_complexity`, `convert_to_field_complexity`, `is_field_nullable`, `is_input_hidden`, `is_input_only`, `is_input_required`, `is_many`, `extend_expression`.
- Docs show how to support new references for Entrypoints, Fields, FederationFields, Inputs, Filters, Orders, Interfaces, Unions, and custom model fields. Registration in `AppConfig.ready`.
- Pluggable classes via settings: `EXECUTOR_CLASS` (graphql-core executor, default `UndineExecutor`), `OPTIMIZER_CLASS`, `SDL_PRINTER`, `DOCSTRING_PARSER`, `SUBSCRIPTION_BROKER_CLASS`.
- Custom pagination handlers, custom validation rules, custom lifecycle hooks, custom scalars, custom directives.
- Dotted-path callbacks: `REQUEST_CACHE_*_PREDICATE`, `REQUEST_CACHE_EXTRA_CONTEXT`, `ERROR_MASKING_PREDICATE`, `PERSISTED_DOCUMENTS_PERMISSION_CALLBACK`, `WEBSOCKET_*_HOOK`, tracing callbacks.

## 31. Settings index (all settings in `undine/settings.py`)

- Schema and naming: `SCHEMA`, `AUTOGENERATION`, `CAMEL_CASE_SCHEMA_FIELDS`, `ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`, `DOCSTRING_PARSER`, `SDL_PRINTER`, `RESOLVER_ROOT_PARAM_NAME`, `ROOT_VALUE`, `MUTATION_INPUT_DATA_KEY`, `QUERY_TYPE_FILTER_INPUT_KEY`, `QUERY_TYPE_ORDER_INPUT_KEY`, `TOTAL_COUNT_PARAM_NAME`, `MUTATION_INPUT_DATA_TYPES_MODULE`.
- Execution: `ASYNC`, `EXECUTOR_CLASS`, `OPTIMIZER_CLASS`, `EXECUTION_TIMEOUT_SECONDS`, `ADDITIONAL_LIFECYCLE_HOOKS`, `ADDITIONAL_VALIDATION_RULES`, `EXPERIMENTAL_DISABLE_ERROR_PROPAGATION`, `EXPERIMENTAL_FRAGMENT_ARGUMENTS`, `EXPERIMENTAL_INCREMENTAL_DELIVERY`, `INCREMENTAL_DELIVERY_EARLY_EXECUTION`, `INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL`.
- Limits and security: `ALLOW_INTROSPECTION_QUERIES`, `ALLOW_DID_YOU_MEAN_SUGGESTIONS`, `MAX_ALLOWED_ALIASES`, `MAX_ALLOWED_DIRECTIVES`, `MAX_ERRORS`, `MAX_FILTERS_PER_TYPE`, `MAX_ORDERS_PER_TYPE`, `MAX_LIST_NESTING_DEPTH`, `MAX_QUERY_COMPLEXITY`, `MAX_TOKENS`, `LIST_ENTRYPOINT_LIMIT`, `MUTATION_INSTANCE_LIMIT`, `FILE_UPLOAD_ENABLED`.
- Errors: `ERROR_MASKING_MESSAGE`, `ERROR_MASKING_PREDICATE`, `INCLUDE_ERROR_TRACEBACK`, `NO_ERROR_LOCATION`.
- Mutations: `MUTATION_FULL_CLEAN`.
- Filtering, ordering, optimizer: `EMPTY_VALUES`, `DISABLE_ONLY_FIELDS_OPTIMIZATION`, `PG_TEXT_SEARCH_PREFIX`, `PREFETCH_HACK_CACHE_KEY`.
- Pagination: `PAGINATION_PAGE_SIZE`, `PAGINATION_INDEX_KEY`, `PAGINATION_ORDERING_KEY`, `PAGINATION_START_INDEX_KEY`, `PAGINATION_STOP_INDEX_KEY`, `PAGINATION_TOTAL_COUNT_KEY`, `PAGINATION_MEMBER_RANK_KEY` (undocumented, used for union/interface pagination).
- Caching: `ENTRYPOINT_DEFAULT_CACHE_TIME`, `REQUEST_CACHE_ALIAS`, `REQUEST_CACHE_PREFIX`, `REQUEST_CACHE_EXTRA_CONTEXT`, `REQUEST_CACHE_READ_PREDICATE`, `REQUEST_CACHE_WRITE_PREDICATE`, `PARSE_CACHE_MAX_SIZE`, `VALIDATION_CACHE_MAX_SIZE`.
- Visibility: `VISIBILITY_CACHE_ALIAS`, `VISIBILITY_CACHE_EXTRA_CONTEXT`, `VISIBILITY_CACHE_PREFIX`, `VISIBILITY_CACHE_TIMEOUT`, `VISIBILITY_MEMO_ATTRIBUTE`.
- Persisted documents: `PERSISTED_DOCUMENTS_ONLY`, `PERSISTED_DOCUMENTS_PATH`, `PERSISTED_DOCUMENTS_PERMISSION_CALLBACK`, `PERSISTED_DOCUMENTS_VIEW_NAME`, `AUTOMATIC_PERSISTED_QUERIES`, `UNDINE_PERSISTED_DOCUMENTS_MODEL` (top-level).
- HTTP and GraphiQL: `GRAPHQL_PATH`, `GRAPHQL_VIEW_NAME`, `GRAPHIQL_ENABLED`, `GRAPHIQL_SSE_ENABLED`, `GRAPHIQL_SSE_SINGLE_CONNECTION`.
- Transports: `ALLOW_QUERIES_WITH_MULTIPART_MIXED`, `ALLOW_MUTATIONS_WITH_MULTIPART_MIXED`, `ALLOW_QUERIES_WITH_SSE`, `ALLOW_MUTATIONS_WITH_SSE`, `ALLOW_QUERIES_WITH_WEBSOCKETS`, `ALLOW_MUTATIONS_WITH_WEBSOCKETS`, `MULTIPART_MIXED_HEARTBEAT_INTERVAL`, `SSE_KEEP_ALIVE_INTERVAL`, `SSE_OPERATION_STREAM_OPEN_TIMEOUT`, `SSE_STREAM_SESSION_PREFIX`, `SSE_TOKEN_HEADER_NAME`, `SSE_TOKEN_QUERY_PARAM_NAME`, `USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1`, `WEBSOCKET_CONNECTION_INIT_HOOK`, `WEBSOCKET_CONNECTION_INIT_TIMEOUT_SECONDS`, `WEBSOCKET_PATH`, `WEBSOCKET_PING_HOOK`, `WEBSOCKET_PONG_HOOK`.
- Subscriptions: `SUBSCRIPTION_BROKER_CLASS`.
- Federation: `FEDERATION_VERSION` and `FEDERATION_*_EXTENSIONS_KEY` keys.
- Integrations: `MODELTRANSLATION_INCLUDE_TRANSLATABLE`, `MODELTRANSLATION_INCLUDE_TRANSLATIONS`, `OPENTELEMETRY_*`, `DATADOG_*`, `SENTRY_*`.
- Testing: `TESTING_CLIENT_FULL_STACKTRACE`, `TESTING_CLIENT_NO_ASYNC_TIMEOUT`.
- Extension keys: one `*_EXTENSIONS_KEY` per element type, plus `REQUEST_CACHE_ACTIVE_EXTENSIONS_KEY`, `VISIBILITY_ACTIVE_EXTENSIONS_KEY`, `SCHEMA_DIRECTIVES_EXTENSIONS_KEY`.

## 32. Optional extras (pyproject.toml)

- `image` (pillow), `debug` (django-debug-toolbar), `channels` (channels), `federation-tracing` (protobuf), `opentelemetry` (opentelemetry-api), `datadog` (ddtrace), `sentry` (sentry-sdk).
- Entry points: mypy plugin `mypy_undine`, pytest plugin `pytest_undine.fixtures`.
- Supported: Python 3.12 to 3.15, Django 5.2, 6.0, 6.1.

## 33. Cross-cutting "not supported" summary (explicit or clear from code)

- No query batching over HTTP.
- No `subscriptions-transport-ws` legacy protocol.
- No `@defer`/`@stream` outside multipart/mixed, and only in async mode.
- No DataLoaders in sync mode.
- No `@atomic` in async mode.
- Visibility is not a security boundary. Hooks are sync only.
- No plural `nodes` entrypoint for Relay. No `nodes` shortcut on connections.
- No page-number pagination.
- No cache invalidation on writes. No mutation result caching.
- No schema-first (SDL-first) development. Code-first only, model-centric.
- No built-in rate limiting or query cost based on rows (complexity counts queries, nesting rule bounds rows).
- No non-Django ORM data sources for QueryTypes (function entrypoints and fields cover other sources).
