# Saleor findings

Version checked: `main` at 3.24.0-a.0 (unreleased). Latest releases: 3.23.36, 3.22.71, 3.21.71 (2026-09-24). Saleor keeps three minor lines patched at the same time.
Saleor is an e-commerce app, not a library. The GraphQL layer is in `saleor/graphql/`. The schema is about 38 800 SDL lines and about 1 450 named types (`saleor/graphql/schema.graphql`).
It pins old versions: `graphene<3.0`, `graphql-core>=2.3.2,<3`, `graphql-relay<3`, `promise~=2.3`. Execution is sync with Promise-based dataloaders. It does not use graphene-django. It copies a small part of it (form field converter) into `saleor/graphql/core/types/converter.py`.
Other GraphQL-related deps: `django-filter~=26.1`, `pydantic>=2.13` (input and webhook response validation), OpenTelemetry.
Most of the items below are infrastructure Saleor had to build itself on top of graphene 2.

## Schema assembly

- `saleor/graphql/api.py`: `Query` and `Mutation` are built by multiple inheritance of per-app classes (`ProductQueries`, `OrderMutations`, ...).
- `build_federated_schema(Query, mutation=, types=, subscription=, directives=)` in `core/federation/schema.py`: wraps `graphene.Schema` and adds `_entities`, `_service`, `_Any`, `_Entity`.
- Extra `types=` list registers types that are not reachable from root fields (webhook payload types, unit enums, payment types, assigned attribute types).
- Custom schema directives: `@doc(category: String!)` groups types and fields into doc categories. `@webhookEventsInfo(asyncEvents:, syncEvents:)` marks which webhook events a mutation or field triggers.
- `schema_printer.py`: own SDL printer. It prints the custom directives on types and fields (graphene 2 printer does not).
- `python manage.py get_graphql_schema`: export SDL. `schema.graphql` is committed and regenerated on every change. Used for API changelog and docs generation.
- `monitor_fields_usage(schema)`: wraps resolvers of deprecated fields and of fields with `BaseField(monitor_usage=True)`. Each call records the `saleor.graphql.field.usage` OTel metric. Used to see if deprecated fields are still in use.
- Description helpers in `core/descriptions.py`: `ADDED_IN_3XX`, `DEPRECATED_IN_3X_INPUT`, `PREVIEW_FEATURE`, `RICH_CONTENT`, `CHANNEL_REQUIRED`. Every new field must carry an `ADDED_IN_*` note (rule in `saleor/graphql/AGENTS.md`).
- Input fields cannot be deprecated in graphene 2. Saleor appends "DEPRECATED: this field will be removed." to the description instead.
- Deprecation policy: fields are deprecated in 3.x and removed in a later minor. Breaking changes are listed per release.

## Base classes for types (`saleor/graphql/core/types/`)

- `BaseObjectType`, `BaseInputObjectType`, `BaseEnum`, `BaseInterface`, `BaseConnection`: thin graphene subclasses that accept `doc_category=` and `webhook_events_info=` in `Meta`.
- `ModelObjectType[MT]` (`core/types/model.py`): object type with `Meta.model`. It does not generate any fields from the model. Every field is declared by hand with a description. Provides `get_node` and `get_model`. Doc category is taken from `DOC_CATEGORY_MAP` by `app_label.Model`.
- No auto model-to-type mapping, no `fields = "__all__"`. This is a deliberate choice for a public API with stable descriptions.
- `ChannelContextType` / `ChannelContextTypeForObjectType`: the resolver root is `ChannelContext(node, channel_slug)`. The default resolver unwraps `root.node`. Used to thread a request-scoped "channel" parameter (market or currency) down the whole tree.
- `ChannelQsContext(qs, channel_slug)`: same idea for querysets.
- `SyncWebhookControlContext(node, allow_sync_webhooks)`: wraps a node to control if nested resolvers may fire sync webhooks.
- `NonNullList(of_type)`: `[T!]` helper. Used almost everywhere.
- `SecureGlobalID`: returns an empty ID for newly created users (hides the ID).
- `JSONString` (`core/fields.py`): returns `None` on invalid JSON instead of an error.
- Custom scalars (`core/scalars.py`): `Decimal` (as Float), `PositiveDecimal`, `JSON` (GenericScalar), `WeightScalar`, `UUID`, `DateTime`, `Date`, `NonNegativeInt`, `PositiveInt`, `Minute`, `Hour`, `Day`, `Metadata`, `Upload`, `_Any`.
- Reusable value types: `Money`, `TaxedMoney`, `MoneyRange`, `TaxedMoneyRange`, `Weight`, `Image`, `File`, `CountryDisplay`, `LanguageDisplay`.
- `ThumbnailField(Image, size=, format=)`: image field with resize and format (`WEBP`, `AVIF`, `ORIGINAL`) arguments. Thumbnails are loaded with `BaseThumbnailBySizeAndFormatLoader`.
- `@traced_resolver` (`core/tracing.py`): OTel span per resolver call.

## Fields (`saleor/graphql/core/fields.py`)

- `BaseField(graphene.Field)`: adds `doc_category=`, `webhook_events_info=[WebhookEventInfo(...)]`, `monitor_usage=`. Webhook info is appended to the description automatically.
- `PermissionsField(..., permissions=[...])`: wraps the resolver in `one_of_permissions_required`. Appends "Requires one of the following permissions: ..." to the description (`auto_permission_message=False` to turn off).
- `ConnectionField`: adds `first`, `last`, `before`, `after` with descriptions that state the page limit. Requires an explicit connection type.
- `FilterConnectionField`: adds `filter=` (legacy) and `where=` inputs. It passes the filterset classes to the resolver through hidden kwargs.
- `TranslationField(TranslationType, type_name=)`: `translation(languageCode: LanguageCodeEnum!)` field resolved through per-model translation dataloaders.
- Nested list fields with a `limit: Int = 100` argument (`DEFAULT_NESTED_LIST_LIMIT`). Each such field must also be added to the cost map.

## Mutations (`saleor/graphql/core/mutations.py`)

- `BaseMutation(graphene.Mutation)`: the base for about 130 mutations. `Meta` options: `description` (required), `error_type_class` (required), `error_type_field`, `permissions` (tuple), `auto_permission_message`, `doc_category`, `errors_mapping`, `support_meta_field`, `support_private_meta_field`, `webhook_events_info`, `exclude`.
- `BaseMutation.mutate`: forces the primary DB (`disallow_replica_in_context`), resolves the lazy user, calls `check_permissions`, runs `perform_mutation`, catches Django `ValidationError`, and converts it to typed errors.
- `check_permissions(context, permissions=None, require_all_permissions=False, **data)`: override hook for object-level checks (for example the `OWNER` filter).
- Helpers: `get_node_or_error(info, id, field=, only_type=, qs=)`, `get_nodes_or_error(ids, field, only_type=)`, `get_global_id_or_error`. They raise `ValidationError` on the right input field.
- `DeprecatedModelMutation`: the old model-bound mutation. `Meta.model`, `object_type`, `return_field_name`, `instance_tracker_fields`. Flow is `get_instance` then `clean_input` (auto resolves ID fields, ID list fields and `Upload` fields) then `construct_instance` then `clean_instance` (`full_clean` with `exclude`) then `save` then `_save_m2m` then `post_save_action` then `success_response`. It still has about 140 subclasses. The docstring says new code should inherit `BaseMutation` because the model mutation inherits too much behavior.
- `ModelWithExtRefMutation`: target object can be selected by `id` or by `externalReference`.
- `ModelWithRestrictedChannelAccessMutation`, `ModelDeleteWithRestrictedChannelAccessMutation`, `BaseBulkWithRestrictedChannelAccessMutation`: add a per-channel permission check.
- `ModelDeleteMutation`, `ModelBulkDeleteMutation`, `BaseBulkMutation(ids: [ID!]!)`: delete and bulk actions. Bulk deletes are limited to 100 ids per call (`BULK_DELETE_LIMIT`, 3.24).
- New bulk mutations (`productBulkCreate`, `productVariantBulkUpdate`, `orderBulkCreate`, `attributeBulkCreate`, `stockBulkUpdate`, `customerBulkUpdate`, `*BulkTranslate`) take `errorPolicy: ErrorPolicyEnum`. Values: `REJECT_EVERYTHING` (default, nothing is saved if any row fails), `REJECT_FAILED_ROWS`, `IGNORE_FAILED` (save the valid part of a row). Results are per row with `BulkError(path, message, code)`.
- `BaseTranslateMutation` / `BaseTranslateMutationWithSlug` (`translations/mutations/utils.py`): generic `xxxTranslate(id:, languageCode:, input:)` mutations.
- Metadata inputs: mutations with `support_meta_field=True` accept `metadata` / `privateMetadata` lists in the same call.
- `FileUpload` mutation (`fileUpload(file: Upload!)`): standalone upload that returns a URL. File type and image checks in `core/validators/file.py` (`validate_upload_file`, MIME sniffing, EXIF check, allowed extensions).
- Reordering: `perform_reordering(qs, operations)` in `core/utils/reordering.py`. Mutations take `moves: [{id, sortOrder}]` with relative moves.
- Pydantic input validation: complex inputs are validated with a pydantic model. `pydantic_to_validation_error(exc, default_error_code=)` in `saleor/graphql/error.py` maps pydantic errors to Django `ValidationError` with codes.
- Mutation count limit: `GRAPHQL_MUTATION_COUNT_LIMIT` (default 4 root mutation fields per operation).
- Mutations run with the primary DB. Queries run with the read replica. See "Database".
- No nested writes as a general feature. Nested inputs are handled by hand per mutation.
- No generic auto-generated CRUD. Every mutation is written by hand.

## Errors

- Two error channels. Query-level errors go to top-level `errors` (syntax, validation, permission denied). Data-level errors are fields in the mutation payload.
- Every mutation payload has `errors: [XxxError!]!`. Many also keep a legacy duplicate field (for example `accountErrors`) set by `Meta.error_type_field`.
- `Error` base type: `field: String` (camelCase input field name or null), `message: String`. Subclasses add `code: XxxErrorCode!` and extra fields (for example `AccountError.addressType`, `ProductError.attributes`, `values`). About 70 error types in `core/types/common.py`.
- Rule: each mutation has its own error class and error code enum (`saleor/graphql/AGENTS.md`). Error codes are Python `Enum`s in `<app>/error_codes.py`, exposed with `graphene.Enum.from_enum`, and registered in `SALEOR_ERROR_CODE_ENUMS` (`core/utils/error_codes.py`).
- `validation_error_to_error_type(validation_error, error_type_class)`: maps `ValidationError.error_dict` to typed errors. `NON_FIELD_ERRORS` gives `field: null`. `ValidationError.params` keys that match error type fields are copied onto the error (`attach_error_params`).
- `get_error_code_from_error`: maps built-in Django codes (`required`, `unique`, `invalid`, ...) to Saleor codes.
- `BulkError(path, message, code)`: error with a dotted path into the input (for example `variants.1.stocks.0.warehouse`).
- `errors_mapping` Meta option: rename error field names.
- Docs tell clients that `message` is for debugging only. Clients must use `code`.
- Top-level error formatting (`saleor/graphql/utils/format_error`): `extensions.exception.code` is the exception class name (for example `PermissionDenied`). Only errors in `ALLOWED_ERRORS` (`GraphQLError`, `PermissionDenied`, `ValidationError`, `InvalidTokenError`, `QueryCostError`, `CircularSubscriptionSyncEvent`) keep their message. Other exceptions become "Internal Server Error" unless `DEBUG`. With `DEBUG`, a stacktrace is added to `extensions`.
- Handled and unhandled errors go to different loggers (`handled_errors_logger`, `unhandled_errors_logger`).
- `PermissionDenied` message lists the required permissions: "You need one of the following permissions: MANAGE_STAFF".
- Memory hygiene: `clear_errors`, `clear_traceback_locals` and patches in `graphql_core.py` and `promise.py` break reference cycles in graphql-core 2 errors and promises.

## Permissions and auth

- Permission enums per domain (`saleor/permission/enums.py`): `ProductPermissions.MANAGE_PRODUCTS`, `OrderPermissions.MANAGE_ORDERS`, and so on. They map to Django `Permission` codenames. Exposed as `PermissionEnum` in GraphQL.
- `AuthorizationFilters` (`saleor/permission/auth_filters.py`): pseudo-permissions mixed into the same list. `AUTHENTICATED_APP`, `AUTHENTICATED_STAFF_USER`, `AUTHENTICATED_USER`, `OWNER`. `OWNER` has no function. Each mutation checks ownership itself.
- `one_of_permissions_or_auth_filter_required(context, perms)`: pass if any permission or any filter matches. `all_permissions_required`: all permissions plus any filter.
- Resolver decorators (`saleor/graphql/decorators.py`): `@permission_required(perm)`, `@one_of_permissions_required([...])`, `@staff_member_required`, `@staff_member_or_app_required`, `@check_attribute_required_permissions()` (permission depends on the root object type), `account_passes_test(fn)`.
- Permission requirements are appended to field and mutation descriptions automatically. Clients can see them in introspection.
- Two principal types: `User` (customer or staff) and `App`. `get_user_or_app_from_context(context)` returns `context.app or context.user`. App permissions are set on install.
- Dashboard extension tokens: JWT whose permissions are the intersection of user and app permissions.
- Channel-restricted permission groups: a staff group can be limited to some channels. `check_channel_permissions(info, channel_ids)` in mutations.
- Field-level visibility of private data: `privateMetadata`, draft/unpublished products need permissions. Unpublished objects are filtered out of querysets for requestors without permission (`ALL_PRODUCTS_PERMISSIONS`).
- `webhookDryRun` checks the same permissions as the event being tested.
- No schema hiding per viewer. All fields are visible in introspection. Access is checked at resolve time.
- `Shop.allowStorefrontTraffic = false` (3.23, `saleor/graphql/storefront_traffic.py`): rejects every request from anonymous users and customers with HTTP 401 and `STOREFRONT_TRAFFIC_NOT_ALLOWED` before execution. Also blocks introspection and login mutations. Setting is cached per site.
- Auth: JWT access and refresh tokens (RS256). JWKS at `/.well-known/jwks.json`. Headers `Authorization: Bearer` or `Authorization-Bearer`. Mutations `tokenCreate`, `tokenRefresh`, `tokenVerify`, `tokensDeactivateAll`. OIDC plugin with `saleor:<permission>` OAuth scopes. External auth mutations `externalAuthenticationUrl`, `externalObtainAccessTokens`, `externalRefresh`, `externalVerify`, `externalLogout`.
- `passwordLoginMode` (`ENABLED`, `CUSTOMERS_ONLY`, `DISABLED`): a staff user who logs in with a password gets no staff permissions in `CUSTOMERS_ONLY` mode.
- Login throttling with exponential block time per IP. Password reset throttling (`RESET_PASSWORD_LOCK_TIME`).
- Context setup (`saleor/graphql/context.py`): `get_context_value(request)` sets `dataloaders`, `allow_replica`, `request_time`, `app`, lazy `user` (`SimpleLazyObject`), `decoded_auth_token`. The context is the Django `HttpRequest` typed as `SaleorContext`.

## Filtering

- Two filter systems in parallel on one connection field. Using both at once is an error.
- Legacy `filter: XxxFilterInput`: `FilterInputObjectType(Meta.filterset_class=...)` builds a flat input from a django-filter `FilterSet`. Invalid filter input raises `GraphQLError` with the form errors as JSON.
- New `where: XxxWhereInput`: `WhereInputObjectType` (`core/filters/where_input.py`) adds `AND: [Self!]` and `OR: [Self!]` fields. `NOT` is commented out in the code ("needs optimization").
- `where` rules: operators and flat fields cannot be mixed at one level. Only one operator per level. Flat fields are combined with AND. Nesting is allowed.
- Operator inputs per scalar: `StringFilterInput{eq, oneOf}`, `IntFilterInput{eq, oneOf, range}`, `DecimalFilterInput`, `DateFilterInput`, `DateTimeFilterInput` (with `range: {gte, lte}`), `GlobalIDFilterInput{eq, oneOf}`, `UUIDFilterInput`, `PriceFilterInput{currency, amount}`, `ContainsFilterInput{containsAny, containsAll}`, `MetadataFilterInput{key, value{eq, oneOf}}`.
- Only one operation per field input (`eq` or `oneOf`, not both).
- Explicit null semantics: `{eq: null}` on a nullable field matches null values. `{eq: null}` on a non-null field returns an empty list. An empty `ids: []` returns an empty list.
- `WhereFilterSet`, `WhereFilter`, `ObjectTypeWhereFilter`, `OperationObjectTypeWhereFilter`, `ListObjectTypeWhereFilter`, `EnumWhereFilter`, `GlobalIDWhereFilter`, `GlobalIDMultipleChoiceWhereFilter` (`core/filters/where_filters.py`): django-filter based filter classes that map to the operator inputs.
- `where_filter_qs` evaluates `AND` by chaining `&` on querysets. `OR` is built by `|` of sub-querysets. Implementation is recursive.
- Global ID filters: `GlobalIDFilter`, `GlobalIDMultipleChoiceFilter` are auto-used for FK, O2O, M2M and reverse relations (`GraphQLFilterSetMixin.FILTER_DEFAULTS`).
- Metadata filtering on public metadata (`filter_where_metadata`). Attribute-value filtering by type (numeric, boolean, date, reference with `containsAll`/`containsAny`).
- Filters with channel context: the channel is taken from the root `channel` argument or the parent `ChannelContext`.
- Rule: each new filtered field needs a DB index created concurrently (`AGENTS.md`).
- `where` is only on some types (`Product`, `ProductVariant`, `Attribute`, `Promotion`, `Order`, `Customer`, `Page`, ...). The rest still use `filter`.

## Search

- Root-level `search: String` argument and `filter.search` (3.23). Postgres full-text search over denormalized search vectors per model.
- Query syntax: prefix match per term, implicit AND, `OR`, `-term` for NOT, `"exact phrase"`. Case and accent insensitive. Special characters become spaces.
- Results sort by relevance (`RANK` sort field) when searching. Keyset cursor for rank uses a Decimal epsilon range (`_prepare_filter_by_rank_expression`). `RANK` without search is an error.

## Ordering

- `sortBy: XxxSortingInput{field: XxxSortField!, direction: OrderDirection!}` (`SortInputObjectType`, `core/types/sort_input.py`). Single sort key only. No list of sort keys.
- Sort enum values are lists of model fields used as tie-breakers: `NAME = ["name", "slug"]`.
- Custom sort: static method `qs_with_<enum_name>(queryset, channel_slug=)` on the enum annotates the queryset first.
- `attributeId` sort for products: sort by an attribute value.
- `ChannelSortInputObjectType`: adds a deprecated per-sort `channel` argument.
- Default ordering from model `Meta.ordering` (`sort_queryset_by_default`).
- No nulls-first/last option.

## Pagination

- Relay connections everywhere: `XxxCountableConnection` with `edges`, `pageInfo`, `totalCount`. `NonNullConnection` makes `edges: [Edge!]!` and `node: T!`. `CountableConnection` adds lazy `totalCount` (runs `qs.count()` only when selected).
- Keyset (seek) pagination (`connection_from_queryset_slice`, `core/connection.py`): the cursor is base64 JSON of the sort key values of the row. `_prepare_filter` builds the `(a > x) OR (a = x AND b > y)` filter. Handles NULL values in sort keys. Fetches `first + 1` rows to compute `hasNextPage`.
- Cursors are declared unstable. Clients must reset pagination when a cursor is rejected.
- Arg rules: `first` and `last` cannot be combined. `first` with `before` and `last` with `after` are errors. Values must be positive.
- `GRAPHQL_PAGINATION_LIMIT = 100`. `first`/`last` above the limit are capped (`max_limit`). `first` or `last` is required only if `edges` is selected (`_is_first_or_last_required`). A query for only `totalCount` needs no `first`.
- `create_connection_slice(iterable, info, args, connection_type)`: chooses queryset keyset pagination or list slicing for dataloader results (`slice_connection_iterable`). The list path is aligned with the queryset path for `hasPreviousPage`.
- `hasNextPage` is only computed for `first`. `hasPreviousPage` is only computed for `last`. Presence of a cursor sets the other one to true.
- No offset or page-number pagination. No root `node(id:)` / `nodes(ids:)` query even though types implement `relay.Node`. Single-object lookup is a per-type root field (`product(id:, slug:, externalReference:, channel:)`).

## Dataloaders and N+1

- `DataLoader[K, R]` (`core/dataloaders.py`) on `promise.dataloader.DataLoader`. `context_key` class attribute. One instance per request stored in `context.dataloaders`. Asserts that a loader is not shared between threads. Each batch is an OTel span with the row count.
- Loaders pick the DB connection (replica or primary) from the context (`database_connection_name`).
- About 160 hand-written loaders (`<app>/dataloaders.py`). Naming pattern `XxxByIdLoader`, `XxxByProductIdLoader`, `...ByIdAndLanguageCodeLoader`. Composite keys are tuples.
- Loaders are chained with `.then()` for multi-hop relations.
- Rule: resolvers must use a dataloader for any relation (`AGENTS.md`).
- `clear_context(context)`: clears loader caches and Django `fields_cache` after the request to break cycles.
- No query optimizer. No automatic `select_related` / `prefetch_related` from the selection set. Batching is manual only.

## Query limits and security

- Query cost (`core/validators/query_cost.py`, `CostValidator` validation rule): static analysis before execution. `COST_MAP` in `saleor/graphql/query_cost_map.py` gives per type and field `{"complexity": n, "multipliers": ["first", "last", "limit"]}`. Cost multiplies down the tree.
- `GRAPHQL_QUERY_MAX_COMPLEXITY` (default 50 000, `0` disables). Over-limit queries fail with `QueryCostError`.
- Response always has `extensions.cost = {requestedQueryCost, maximumAvailable}` when the limit is on.
- Rule: every new field with a `limit` argument must be added to the cost map (`AGENTS.md`).
- `AliasCountLimitRule`: `GRAPHQL_ALIAS_COUNT_LIMIT` (default 100).
- `MutationCountLimitRule`: `GRAPHQL_MUTATION_COUNT_LIMIT` (default 4).
- `GRAPHQL_BATCH_MAX_COUNT` (default 1): JSON array batching of operations, off by default.
- `FEDERATED_QUERY_MAX_ENTITIES` (default 100): cap on `_entities(representations:)`.
- Input list size limit of 100 by convention, documented in descriptions.
- Request body too large gives HTTP 413.
- No depth limit rule. Cost limit covers it.
- No persisted queries or allow lists.
- Introspection is not disabled. Pure introspection queries are cached (see "Serving").

## Federation

- Apollo Federation v1 style subgraph, hand-built (`saleor/graphql/core/federation/`). No graphene-federation dependency.
- `@federated_entity("id")` / `@federated_entity("id channel")` decorator registers the type in `federated_entities` and prepends `@key(fields: ...)` to its SDL.
- Per type `__resolve_references(roots, info)` classmethod. `resolve_federation_references(graphql_type, roots, queryset)` batches all ids of one type into one query.
- `_entities` validates `__typename`, unknown fields, and the entity count. Representation keys are snake_cased.
- `_service { sdl }` prints the schema without subscriptions and injects `@key` directives by string edits.
- Composite keys (`id channel`) and alternative keys (`User` by `id` or `email`).
- No `@external`, `@requires`, `@provides`, `@shareable`, `@link`. No Federation v2.

## Webhooks and subscriptions

- The schema has a real `Subscription` root type. It is only used to define webhook payloads. Executing a subscription over HTTP returns "Subscriptions are supported only as webhooks". No WebSocket, SSE, or graphql-ws transport.
- Webhook payload = a subscription document stored on the webhook (`webhookCreate(input: {query: "subscription { event { ... on ProductUpdated { product { id name } } } }"})`). The server runs it with `allow_subscriptions=True` and root `(event_type, object)` (`generate_payload_from_subscription`, `saleor/graphql/webhook/subscription_payload.py`).
- The payload is built with the same resolvers and permissions as the API. The app's permissions apply. Missing permissions give `errors` in the payload.
- `initialize_request(app, requestor, sync_event, allow_replica, event_type, request_time, dataloaders)`: builds a fake request as context. Dataloaders are shared across webhooks of one event.
- `Event` interface with `issuedAt`, `version`, `issuingPrincipal: App | User`, `recipient`. About 170 subscription payload types (`WEBHOOK_TYPES_MAP`).
- Filterable subscriptions: top-level fields like `orderCreated(channels: [String!])` instead of `event`. Only one top field per filterable subscription. Channels list max 500 (`SubscriptionQuery.get_filterable_channel_slugs`).
- `SubscriptionQuery` (`saleor/graphql/webhook/subscription_query.py`): validates the stored document and extracts event types from inline fragments.
- Sync webhooks: called during the request and their JSON response changes the result (taxes, shipping, payments). Responses are validated with pydantic (`saleor/webhook/response_schemas`). Published JSON Schemas in `saleor/json_schemas/`.
- Circular protection: fields that trigger sync webhooks cannot be selected in sync webhook payloads. They raise `CircularSubscriptionSyncEvent`.
- Async webhooks: Celery tasks with delivery records, up to 5 retries with backoff, `eventDeliveryRetry` mutation. Transports by URL scheme: HTTP(S), `gcpubsub://`, `awssqs://`.
- Signature: `Saleor-Signature` header with detached JWS (RS256) checked against JWKS. Legacy HMAC-SHA256 with `secretKey`. Headers `Saleor-Event`, `Saleor-Domain`, `Saleor-Api-Url`. Custom headers (max 5).
- `webhookDryRun(objectId:, query:)`: render a payload without sending. `webhookTrigger`: send one real event for a webhook, for testing.
- Circuit breaker per app for sync webhooks (`saleor/webhook/circuit_breaker`, Redis, `BREAKER_BOARD_*` settings, dry run mode, `App.breakerState`, `appReenableSyncWebhooks`).
- `webhook_events_info` on mutations and fields documents which events fire. Shown in descriptions and in the `@webhookEventsInfo` directive.
- Observability webhooks: API calls and deliveries are buffered and reported, with sensitive fields and headers obfuscated (`saleor/webhook/observability/sensitive_data.py`).

## Metadata

- `ObjectWithMetadata` interface (`saleor/graphql/meta/types.py`): `metadata: [MetadataItem!]!`, `metafield(key:)`, `metafields(keys:)`, and the `private*` versions. `Metadata` scalar returns a key-value object.
- Generic mutations on any object by global ID: `updateMetadata`, `deleteMetadata`, `updatePrivateMetadata`, `deletePrivateMetadata`. Permissions are looked up per type (`PUBLIC_META_PERMISSION_MAP`, `PRIVATE_META_PERMISSION_MAP`).
- `privateMetadata` needs manage permission on the object. Public metadata is readable by anyone who can read the object.
- `metadata` and `privateMetadata` also accepted in create and update inputs.
- Metadata changes fire dedicated webhook events (`orderMetadataUpdated`, ...).

## Translations

- Separate translation models per translatable model (`ProductTranslation`, `CategoryTranslation`, ...). GraphQL types with the same name.
- `translation(languageCode: LanguageCodeEnum!)` field on translatable types. Untranslated fields return `null`. The client does the fallback.
- `translations(kind: TranslatableKinds!)` and `translation(kind:, id:)` root queries list translatable content (`TranslatableItem` union, `translatableContent` on each type). Requires `MANAGE_TRANSLATIONS`.
- `xxxTranslate` and `xxxBulkTranslate` mutations. Slugs are translatable.
- `LanguageCodeEnum` generated from Django `LANGUAGES`.
- Schema descriptions are not translated.

## Database

- Read replica routing: queries use `DATABASE_CONNECTION_REPLICA_NAME`. Mutations switch the context to the primary (`disallow_replica_in_context`, `@allow_writer`). `patch_executor()` wraps field completion in `allow_writer_in_context`. Loaders use `get_database_connection_name(context)`.
- `InstanceTracker` (`instance_tracker_fields`): detects which fields changed so that webhooks fire only on real changes.

## Serving and transport

- `GraphQLView` (`saleor/graphql/views.py`): own Django `View`, not graphene-django. Only `POST` runs operations. `GET` renders the playground if `PLAYGROUND_ENABLED`. No GET queries.
- Content types: `application/json`, `application/graphql`, `multipart/form-data` (GraphQL multipart request spec with `operations` and `map`). Upload values are resolved from `request.FILES` in `clean_input`.
- `SaleorGraphQLBackend` + `GraphQLCachedBackend(cache_map=CacheDict(1000))`: parse and validate once and cache the parsed document by query string (LRU of 1000).
- Introspection-only queries are cached in the Django cache by query hash + Saleor version + `GRAPHQL_CACHE_SUFFIX` (not in `DEBUG`).
- HTTP status: 400 for invalid documents, 401 for blocked storefront traffic, 413 for large bodies, 200 otherwise. Batches return the max status.
- `orjson` response serializer. Decimals are serialized as strings.
- `GRAPHQL_MIDDLEWARE` setting: list of dotted paths to graphene middleware (empty by default).
- ASGI app (`saleor/asgi/`) with CORS (`ALLOWED_GRAPHQL_ORIGINS`), gzip, health check, telemetry middleware. The view itself is sync.
- Playground: `@saleor/graphql-playground` (GraphiQL based) in `templates/graphql/playground.html`. Dashboard opens an authenticated playground with `CMD+'`.
- `ENABLE_DEBUG_TOOLBAR`: Django Debug Toolbar on the playground page.
- `source-service-name` request header is recorded on spans.

## Observability

- OpenTelemetry tracing and metrics (3.21, replaced OpenTracing). `saleor.core.telemetry` with `tracer`, `meter`, `Scope.CORE` vs `Scope.SERVICE`. W3C trace context in and out.
- Spans: HTTP request, GraphQL operation (document, operation type, name, cost, app id), each dataloader batch, traced resolvers, webhook calls. Slow requests over `GRAPHQL_SPANS_MARK_SLOW_AFTER` are marked as errors so sampling keeps them.
- `query_identifier(document)`: sorted list of root field names. `query_fingerprint(document)`: `operation:name:md5`.
- Metrics (`saleor/graphql/metrics.py`): query count, query duration, slow operation duration, query cost, request count and duration, batch size, alias count, mutation count, field usage.
- Sentry integration (docs `setup/monitoring-sentry.mdx`, not checked in code).

## Testing

- `ApiClient.post_graphql(query, variables, permissions=, check_no_permissions=)` and `post_multipart` (`saleor/graphql/tests/fixtures.py`). Fixtures `staff_api_client`, `app_api_client`, `user_api_client`, `api_client`, `superuser_api_client`.
- `get_graphql_content(response, ignore_errors=)`, `assert_no_permission(response)` (`saleor/graphql/tests/utils.py`).
- Benchmark tests count SQL queries per operation (`count_queries` fixture, `*/tests/benchmark/`).
- `FakeDbReplicaConnection` to assert replica usage in tests.

## Other infrastructure

- Global IDs: base64 `Type:pk`. `from_global_id_or_error(id, only_type=, raise_error=)`. Some types accept old int IDs and new UUID IDs (`TYPES_WITH_DOUBLE_ID_AVAILABLE`).
- `externalReference`: unique external ID on many models. Lookup by `externalReference` in queries and mutations.
- Slugs are auto-generated from the name when missing.
- Plugins (`BasePlugin`, `PluginsManager`): in-process extension pipeline with `previous_value` chaining. Being deprecated in favor of apps (webhooks).
- Apps: external services with their own tokens, permissions, webhooks, dashboard extensions and an app manifest.
- `promise.py` / `graphql_core.py` patches: `__del__` patches to free memory in graphene 2.
- Agent rules in `saleor/graphql/AGENTS.md`: own error class per mutation, `ADDED_IN_*` tags, list limit 100, cost map entry for `limit` fields, `Meta.permissions` over manual checks, return the mutated object, use dataloaders, avoid mutable `default_value`.

## Not supported or not in scope

- No real-time subscriptions (no WebSocket, SSE, or graphql-ws). Subscriptions only define webhook payloads.
- No automatic type generation from models. No query optimizer. No automatic `only()` / `select_related`.
- No `node(id:)` root query.
- No offset pagination. No multi-key `sortBy` list. No nulls ordering option.
- No `NOT` operator in `where` (planned, commented out).
- No persisted queries or operation allow lists. No depth limit rule.
- No `@defer`, `@stream`, `@oneOf`. graphql-core 2 cannot support them.
- No async execution. No async dataloaders.
- No schema visibility per viewer (hidden fields or types).
- No Federation v2 directives.
- No GET requests for queries. No HTTP caching.
- No i18n of schema descriptions or error messages beyond Django `gettext` in some messages.
- No generic nested mutations or generic CRUD generation.
- No mypy plugin. Typing uses `ModelObjectType[Model]` generics only.

## Sources

Repo: https://github.com/saleor/saleor (shallow clone at `/tmp/saleor`, `main`, version 3.24.0-a.0).
Docs repo: https://github.com/saleor/saleor-docs (shallow clone at `/tmp/saleor-docs`). Source of https://docs.saleor.io/.

Docs read (paths in the docs repo, URLs under https://docs.saleor.io/):
- `docs/api-usage/overview.mdx` (https://docs.saleor.io/api-usage/overview)
- `docs/api-usage/authentication.mdx` (https://docs.saleor.io/api-usage/authentication)
- `docs/api-usage/error-handling.mdx` (https://docs.saleor.io/api-usage/error-handling)
- `docs/api-usage/filtering.mdx` (https://docs.saleor.io/api-usage/filtering)
- `docs/api-usage/pagination.mdx` (https://docs.saleor.io/api-usage/pagination)
- `docs/api-usage/usage-limits.mdx` (https://docs.saleor.io/api-usage/usage-limits)
- `docs/api-usage/apollo-federation.mdx` (https://docs.saleor.io/api-usage/apollo-federation)
- `docs/api-usage/i18n.mdx`, `metadata.mdx`, `search.mdx`, `external-references.mdx`, `slug-fields.mdx`, `developer-tools.mdx`, `prices.mdx`
- `docs/developer/permissions.mdx` (https://docs.saleor.io/developer/permissions)
- `docs/developer/extending/api/sorters.mdx`, `errors.mdx`, `events.mdx`, `i18n.mdx`
- `docs/developer/extending/overview.mdx`, `extending/plugins/overview.mdx`
- `docs/developer/bulks/overview.mdx`, `bulks/error-policy.mdx`
- `docs/developer/extending/webhooks/overview.mdx` (https://docs.saleor.io/developer/extending/webhooks/overview), `subscription-webhook-payloads.mdx`, `payload-signature.mdx`, `asynchronous-events.mdx`
- `docs/developer/extending/webhooks/synchronous-events/overview.mdx`, `circuit-breakers.mdx`
- `docs/setup/configuration.mdx` (GraphQL settings), `setup/telemetry.mdx`, `setup/read-replicas.mdx` (skimmed)

Changelog: `CHANGELOG.md` (only unreleased 3.24). GitHub release notes for 3.20.0, 3.21.0, 3.22.0, 3.23.0 via the GitHub API (https://github.com/saleor/saleor/releases).

Source files checked:
- `saleor/graphql/AGENTS.md`, `api.py`, `views.py`, `context.py`, `graphql_core.py`, `promise.py`, `storefront_traffic.py`, `error.py`, `metrics.py`, `middleware.py`, `decorators.py`, `schema_printer.py`, `query_cost_map.py`
- `saleor/graphql/core/fields.py`, `connection.py`, `mutations.py`, `dataloaders.py`, `context.py`, `descriptions.py`, `doc_category.py`, `enums.py`, `scalars.py`, `tracing.py`, `const.py`
- `saleor/graphql/core/types/base.py`, `model.py`, `context.py`, `common.py`, `sort_input.py`, `converter.py`
- `saleor/graphql/core/filters/where_input.py`, `filter_input.py`, `where_filters.py`, `filters.py`, `shared_filters.py`
- `saleor/graphql/core/validators/__init__.py`, `query_cost.py`, `alias_count_limit_rule.py`, `mutation_count_limit_rule.py`, `file.py`
- `saleor/graphql/core/federation/schema.py`, `entities.py`, `resolvers.py`
- `saleor/graphql/utils/__init__.py`, `utils/sorting.py`, `utils/validators.py`
- `saleor/graphql/webhook/subscription_payload.py`, `subscription_query.py`, `subscription_types.py`, `mutations/`
- `saleor/graphql/translations/fields.py`, `resolvers.py`, `mutations/utils.py`
- `saleor/graphql/meta/types.py`, `meta/permissions.py`
- `saleor/graphql/product/types/categories.py` (example type)
- `saleor/graphql/tests/fixtures.py`, `tests/utils.py`
- `saleor/permission/auth_filters.py`, `permission/utils.py`, `permission/enums.py`
- `saleor/webhook/` (directory layout, `transport/utils.py`, `observability/`)
- `saleor/asgi/`, `saleor/settings.py` (GraphQL settings), `pyproject.toml`
