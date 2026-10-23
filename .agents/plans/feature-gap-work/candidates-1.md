# Candidates batch 1

Findings files: strawberry-django, graphene-django, graphene-django-cud, django-graphql-jwt, saleor, graphene-sqlalchemy, strawberry-sqlalchemy, graphene-pydantic, graphjoiner-graphlayer.

## 2. Query types and fields

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Model property field with optimizer hints | Exposes a model `@property` or cached property as a field and declares what it needs from the database. | strawberry-django: `strawberry_django.descriptors.model_property`, `model_cached_property` | partial: `@Field` method plus `@<field>.optimize` | medium | Undine can do it in two steps. A property reference (`Field(Model.prop)`) is not a supported reference. I checked `convert_to_field_ref`. |
| Field-level optimizer hints as arguments | Declares `only`, `select_related`, `prefetch_related`, `annotate` directly on the field or type. | strawberry-django: `strawberry_django.field(only=, select_related=, prefetch_related=, annotate=)`, `type(..., only=, ...)` | partial: `@<field>.optimize` and `__optimize__` hooks | low | Hooks cover it. Arguments are only a shorter syntax. |
| Disable optimizer per field or type | Turns off the optimizer for one field or type. | strawberry-django: `field(disable_optimization=True)`, `DjangoOptimizerExtension.disabled()` | missing | low | Custom resolvers already bypass it. I think a switch is rarely needed. |
| Type description from model docstring | Uses the model class docstring as the type description. | strawberry-django: `TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING` | partial: QueryType docstring, model field `help_text` | low | Django model docstrings are often not user facing. |
| Default list arguments per type | Sets filters, ordering and pagination once on a type for all list fields that return it. | strawberry-django: `type(..., filters=, ordering=, pagination=True)` | partial: `QueryType(filterset=, orderset=)` | medium | No type-level default pagination. Each `Field` needs its own `Connection` or `OffsetPagination`. |
| Polymorphic model support | Resolves the concrete subclass for multi-table inheritance and optimizes interface queries. | strawberry-django: django-polymorphic and django-model-utils `InheritanceManager` (`select_subclasses`) support | missing | medium | Undine matches unions by exact model class. No grep hits for polymorphic. |

## 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Filtered bulk update and delete | Updates or deletes all rows that match a filter input. | strawberry-django: `mutations.update(Input, filters=F)`, `mutations.delete(filters=F)`, `ALLOW_MUTATIONS_WITHOUT_FILTERS` | missing | medium | Undine bulk mutations take a list of inputs with pk. |
| Lookup by unique field | Finds the object to update or delete by a unique field instead of pk. | strawberry-django: `key_attr=`, `DEFAULT_PK_FIELD_NAME`. saleor: `ModelWithExtRefMutation` (`id` or `externalReference`), per-type root fields like `product(id:, slug:, externalReference:)` | missing | medium | I think `custom` kind can do it by hand. No built-in option. |
| full_clean options | Controls `exclude`, `validate_unique`, `validate_constraints` for `full_clean`. | strawberry-django: `FullCleanOptions(exclude=, validate_unique=, validate_constraints=)` | partial: `MUTATION_FULL_CLEAN` setting (global on or off) | low | Per mutation switch is missing. |
| Through model defaults for many-to-many | Passes extra data to the through model when linking. | strawberry-django: `through_defaults` key in `ListInput` | missing | medium | I think nested related mutations do not handle through fields. No grep hit for `through_defaults`. |
| Explicit add, remove, set for to-many relations | Client chooses to add, remove or replace related links. | strawberry-django: `ListInput[T] { set, add, remove }`, `ManyToManyInput` | partial: related mutations replace the set. `RelatedAction` controls unselected rows | medium | No add-only or remove-only operation. |
| Mutation errors as operation info | Catches Django `ValidationError`, `PermissionDenied`, `ObjectDoesNotExist` and returns a typed message list with field and code. | strawberry-django: `handle_django_errors=True`, `OperationInfo`, `OperationMessage`, `MUTATIONS_DEFAULT_HANDLE_ERRORS`. saleor: `errors: [XxxError!]!` with `code` enums, `validation_error_to_error_type`, `get_error_code_from_error` | partial: `Entrypoint(errors=[...])` errors as data | medium | Undine has errors as data. A default message type with `field` and `code` per Django `ValidationError` is not built in. I think it is easy to add as an error type. |
| Upsert and get-or-create mutation | Creates or updates based on a lookup. | strawberry-django: listed as missing in its own docs | partial: `custom` kind acts as create or update by `pk` | low | Lookup by other fields is missing. |

## 4. Filtering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Nested lookup input objects | Each field gets a typed input with its lookups (`name: {iContains: "x"}`). | strawberry-django: `filter_type(lookups=True)`, `StrFilterLookup`, `DateFilterLookup` | partial: flat filters like `nameIcontains` | low | Different shape. Same power. |
| Nested relation filter input | Filters a relation with the related type's filter set as a nested input. | strawberry-django: `color: ColorFilter \| None` on a filter type | partial: relation path filters on the same FilterSet | medium | Undine uses `Filter("color__name")`. Reuse of a related FilterSet as a nested input is not supported. I think. |
| Filter field that is not applied | Declares an input that only a custom filter method reads. | strawberry-django: `filter_field(skip_queryset_filter=True)` | partial: `__filter_queryset__` on FilterSet | low | I think Undine has no way to read a "parameter" filter in `__filter_queryset__` without applying it. Not verified. |
| GeoDjango filters | Spatial lookups like `intersects`, `within`. | strawberry-django: `GeometryFilterLookup` | missing | low | No gis support in Undine. |
| DISTINCT flag in filter input | Client asks for distinct results. | strawberry-django: `DISTINCT: Boolean` on every filter input | partial: `Filter(distinct=True)` server side | low | Server-side control is safer. |

## 5. Ordering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Client-chosen null placement | Client picks `ASC_NULLS_FIRST`, `DESC_NULLS_LAST` and so on. | strawberry-django: `Ordering` enum | partial: `Order(null_placement=...)` fixed on server | medium | Could add extra enum values per Order. |
| Nested relation ordering input | Orders by a related type's order input. | strawberry-django: `color: ColorOrder \| None` | partial: relation path `Order("color__name")` | low | Same power, different shape. |
| Custom function ordering | Ordering defined by a method that returns expressions. | strawberry-django: `@strawberry_django.order_field` | missing | medium | Inventory lists "No function references for Order". |

## 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Offset pagination wrapper with total count | Offset page with `totalCount`, `pageInfo { limit, offset }`, `results`. | strawberry-django: `OffsetPaginated[T]`, `strawberry_django.offset_paginated()` | partial: `OffsetPagination` returns a plain list | high | Clients often need total count with offset pages. |
| Global max limit for pagination | Caps client limit, including `limit: null`. | strawberry-django: `PAGINATION_MAX_LIMIT`, `connection(max_results=N)` | partial: `page_size` acts as max for offset. `PAGINATION_PAGE_SIZE` default | low | I think Undine already caps with `page_size`. Verify for connections. |
| Offset-based Relay connection | Relay connection with offset slicing cursors. | strawberry-django: `ListConnection`, `DjangoListConnection` | partial: keyset `Connection` only | low | Keyset is better. |

## 7. Global object IDs (Relay Node)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Global ID inputs for mutations | Inputs accept `id: GlobalID` for update and delete. | strawberry-django: `NodeInput`, `NodeInputPartial` | missing | medium | I think Undine mutation inputs use raw `pk`. Not verified. |
| Auto ID as global ID | Maps every model id to a global ID. | strawberry-django: `MAP_AUTO_ID_AS_GLOBAL_ID` | partial: `Node` interface per QueryType | low | |
| Plural node lookup | Fetches many nodes by global IDs. | strawberry-django: `resolve_model_nodes`. saleor: listed as missing (no `nodes(ids:)`) | missing | medium | Inventory lists no `nodes` entrypoint. |

## 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| File output object | File fields output an object with `name`, `path`, `size`, `url`. Images add `width`, `height`. | strawberry-django: `DjangoFileType`, `DjangoImageType` | partial: `File` and `Image` scalars output the URL | medium | Checked `undine/scalars/file.py`. It serializes `value.url`. |
| Range field mapping | Maps Postgres range fields to GraphQL types. | strawberry-django: listed as not mapped | missing | low | Undine has bad lookups for `RangeField` but no type conversion. Checked `convert_to_graphql_type.py`. |
| GeoDjango scalars | `Point`, `Polygon`, `Geometry` and other GIS types. | strawberry-django: geometry scalars | missing | low | Niche. |

## 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Declarative permission classes | Ready classes like `IsAuthenticated`, `IsStaff`, `IsSuperuser`. | strawberry-django: `strawberry_django.permissions.IsAuthenticated`, `IsStaff`, `IsSuperuser` | missing | high | Inventory: no declarative permission classes. |
| Django model permission checks | Checks `user.has_perm` for model or object permissions. | strawberry-django: `HasPerm`, `HasSourcePerm`, `HasRetvalPerm` | missing | high | No `has_perm` integration. |
| Permission-filtered querysets | Filters list results in SQL to objects the user has permission for. | strawberry-django: `HasRetvalPerm`, `filter_for_user`, `filter_with_perms` | partial: `__filter_queryset__` by hand | medium | |
| django-guardian integration | Object-level permissions from guardian tables. | strawberry-django: `strawberry_django.integrations.guardian` | missing | medium | |
| Permission fallback values | On denied access returns null, empty list or empty connection instead of error. | strawberry-django: `HasPerm(fail_silently=True)` | partial: pattern with `__filter_queryset__` | low | |
| Permission directives in SDL | Emits permission info as schema directives. | strawberry-django: `HasPerm(use_directives=True)` | missing | low | Undine directives are metadata, so users can add it. |

## 22. Lifecycle hooks / Authentication

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Session auth mutations | Ready `login`, `logout`, `register`, `currentUser` fields. | strawberry-django: `strawberry_django.auth.login()`, `logout()`, `register()`, `current_user()` | missing | medium | No auth helpers in Undine. I checked with grep. |

## 19. Caching

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Shared validation cache | Caches validation results in the Django cache across processes. | strawberry-django: `DjangoValidationCache`, `DjangoCacheBase` | partial: in-process `ValidationCacheHook` | low | Inventory says no shared document cache on purpose. |

## 25. Tooling, typing and testing

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Test client login context manager | `with client.login(user):` logs in a given user for a block. | strawberry-django: `TestClient.login(user)` | partial: `login_with_superuser`, `login_with_regular_user` | low | I think a "login as this user" helper may be missing. Not verified. |

## 26. Transports and HTTP

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Channels router helper with auth | One router for HTTP and WebSocket with auth middleware and allowed hosts. | strawberry-django: `AuthGraphQLProtocolTypeRouter` | partial: `get_websocket_enabled_app` and friends | low | I think Undine helpers already wrap this. |

## graphene-django additions

### 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Django Form mutations | Builds input from a Django `Form` or `ModelForm` and returns form errors as data. | graphene-django: `DjangoFormMutation`, `DjangoModelFormMutation`, `DjangoFormInputObjectType` | missing | medium | Inventory: no Django forms integration. Lets teams reuse existing forms. |
| DRF serializer mutations | Builds input and output from a DRF serializer. | graphene-django: `SerializerMutation` (`model_operations`, `lookup_field`) | missing | medium | Inventory: no DRF integration. Useful for migration from REST. |
| Field error list type | Returns `errors: [{field, messages}]` in the mutation payload. | graphene-django: `ErrorType`, `CAMELCASE_ERRORS` | partial: errors as data with `Entrypoint(errors=[...])` | low | Close to the strawberry-django `OperationInfo` row. |

### 4. Filtering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| django-filter integration | Uses a `django_filters.FilterSet` as the filter arguments. | graphene-django: `DjangoFilterConnectionField(filterset_class=...)`, `Meta.filter_fields` | missing | low | Undine has its own FilterSet. Could help migration. |
| Global ID filter values | Filters on relations and ids take Relay global IDs. | graphene-django: `GlobalIDFilter`, `GlobalIDMultipleChoiceFilter`. saleor: `GlobalIDFilterInput`, `GlobalIDWhereFilter` | missing | medium | I think Undine filters always take raw pks. Not verified. |
| Array field filters | `contains`, `overlap` lookups on Postgres `ArrayField`. | graphene-django: `ArrayFilter` | partial: autogenerated lookups for `ArrayField` | low | I think autogeneration covers it. `convert_to_bad_lookups` handles `ArrayField`. |

### 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Require first or last | Rejects connection queries without `first` or `last`. | graphene-django: `RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST`, `enforce_first_or_last=` | partial: default `page_size` applies | low | Default page size makes this less needed. |
| Offset argument on connections | Adds `offset` to a Relay connection. | graphene-django: `DjangoConnectionField` `offset` argument | missing | low | Conflicts with keyset design. |

### 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Custom choice enum naming | A setting gives a function that names choice enums. | graphene-django: `DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME`, `Meta.convert_choices_to_enum` | partial: fixed `<Model><Field>Choices` naming | low | Per type opt-out of enum conversion is also missing. I think. |

### 25. Tooling, typing and testing

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| SQL debug field in response | A `_debug` field returns executed SQL and exceptions in the GraphQL response. | graphene-django: `DjangoDebugMiddleware`, `DjangoDebug` | partial: Django Debug Toolbar integration | low | Toolbar covers most use. |
| Schema export as introspection JSON | Writes `schema.json` introspection output. Has a watch mode. | graphene-django: `graphql_schema --out schema.json --watch` | partial: `print_schema` prints SDL only | low | Some client tools still want JSON introspection. |
| unittest TestCase helpers | Test case classes with `query()` and `assertResponseNoErrors`. | graphene-django: `GraphQLTestCase`, `GraphQLTransactionTestCase` | partial: pytest fixtures only | low | Some Django projects use plain `manage.py test`. I did not find `TestCase` in `pytest_undine`. |

### 26. Transports and HTTP

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Query batching | Many operations in one HTTP request as a JSON array. | graphene-django: `GraphQLView(batch=True)`. saleor: `GRAPHQL_BATCH_MAX_COUNT` | missing | medium | Inventory: no query batching. |
| Pretty JSON output | `?pretty` gives indented JSON. | graphene-django: `GraphQLView(pretty=True)` | missing | low | Debug comfort only. |

## graphene-django-cud additions

### 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Row lock on update | Locks the row with `select_for_update()` before update. | graphene-django-cud: `Meta.use_select_for_update=True` | missing | medium | No grep hit for `select_for_update` in `undine/`. Prevents lost updates. |
| Before-save hook | Hook that runs right before save and can change the object. | graphene-django-cud: `before_save`, `before_create_obj`, `before_mutate` | partial: `__validate__`, `@<input>.convert`, function inputs | medium | Undine has `__after__` but no explicit `__before__` hook. Checked `undine/mutation.py`. |
| Mutation-level Django signals | Signals sent once after the whole mutation, including nested relations. | graphene-django-cud: `post_create_mutation`, `post_update_mutation`, `post_delete_mutation` and batch variants | partial: `__after__` hook, model signals | medium | Model `post_save` fires before relations are written. A mutation signal fires after. |
| Soft delete hook | Overrides how delete is done. | graphene-django-cud: `perform_delete(obj)` | partial: `__mutate__` on custom kind | low | I think a delete MutationType with `__mutate__` becomes custom kind. Not verified. |
| Batch delete result details | Returns `deletionCount`, `deletedIds`, `missedIds`. | graphene-django-cud: `DjangoBatchDeleteMutation` | partial: delete returns `{ pk }` | low | Missing ids are not reported. I think. |
| Full replace update | Update where all fields are required (replace semantics) next to patch. | graphene-django-cud: `DjangoUpdateMutation` vs `DjangoPatchMutation` | partial: update is partial only | low | Users can set `required=True` per Input. |
| ID suffix input names | FK inputs named `ownerId`, M2M `enemiesIds`. | graphene-django-cud: `use_id_suffixes_for_fk`, `use_id_suffixes_for_m2m` | partial: `Input(schema_name=...)` per input | low | No global switch. |
| ID inputs accept pk or global ID | One id argument decodes raw pk, UUID or global ID. | graphene-django-cud: `disambiguate_id`, `resolve_id` | missing | low | Related to the global ID inputs row. |
| Input type override per field | Changes the GraphQL type of one generated input. | graphene-django-cud: `Meta.field_types` | partial: `Input(<type>)` reference | low | I think Undine covers it by explicit Input ref. |

### 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Login required flag | One flag rejects anonymous users. | graphene-django-cud: `Meta.login_required` | missing | high | Same gap as declarative permission classes. |
| Model permission list on mutation | Checks `user.has_perms(("app.add_model",))`. | graphene-django-cud: `Meta.permissions`, `get_permissions` | missing | high | Same gap as `HasPerm`. |

### 17. Subscriptions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Subscriptions on mutation signals | Subscriptions fire on the library mutation signals, after nested writes. | graphene-django-cud: `GRAPHENE_DJANGO_CUD_USE_MUTATION_SIGNALS_FOR_SUBSCRIPTIONS` | partial: model signal subscriptions, custom `SignalSubscription` | low | Depends on the mutation signal row. |

## django-graphql-jwt additions

### Authentication (new area)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| JWT token auth | Issues and verifies JSON Web Tokens and sets `request.user` from the token. | django-graphql-jwt: `ObtainJSONWebToken` (`tokenAuth`), `Verify`, `JSONWebTokenMiddleware`, `JSONWebTokenBackend`. saleor: `tokenCreate`, `tokenRefresh`, `tokenVerify`, JWKS at `/.well-known/jwks.json` | missing | medium | Undine relies on Django auth. A Django auth backend from another package also works. So it may be better as docs or an optional extra. |
| Refresh tokens | Long-lived refresh tokens stored in the database. Refresh, rotate and revoke. | django-graphql-jwt: `Refresh` (`refreshToken`), `Revoke` (`revokeToken`), `RefreshToken` model, `JWT_LONG_RUNNING_REFRESH_TOKEN`, `cleartokens` command | missing | low | Big scope. Better left to an auth package. |
| HttpOnly cookie token transport | Stores the token in an HttpOnly cookie and reads it if no header. Logout deletes the cookie. | django-graphql-jwt: `jwt_cookie`, `DeleteJSONWebTokenCookie`, `JWT_HIDE_TOKEN_FIELDS`, `JWT_CSRF_ROTATION` | missing | low | Django sessions already give a cookie flow. |
| Per-argument credentials | A `token` argument on a field authenticates that subtree with another user. | django-graphql-jwt: `JWT_ALLOW_ARGUMENT`, `JWT_ARGUMENT_NAME`, `PathDict` | missing | low | Unusual pattern. |
| Auth signals | Signals on token issue, refresh, rotate and revoke. | django-graphql-jwt: `token_issued`, `token_refreshed`, `refresh_token_rotated`, `refresh_token_revoked` | missing | low | Only matters if Undine ships auth. |
| Test client authenticate as user | Test client sets credentials for a given user. | django-graphql-jwt: `JSONWebTokenClient.authenticate(user)`, `credentials(**headers)` | partial: `login_with_superuser`, `login_with_regular_user`, `headers=` | low | Same as the strawberry-django test login row. |

### 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Permission decorators for resolvers | Decorators like `@login_required`, `@staff_member_required`, `@superuser_required`, `@permission_required("app.perm")`, `@user_passes_test(fn)`. | django-graphql-jwt: `graphql_jwt.decorators.*`. saleor: `@permission_required`, `@one_of_permissions_required`, `@staff_member_required`, `PermissionsField(permissions=[...])` | missing | high | Same gap as declarative permission classes. Undine could ship ready `@<field>.permissions` callables. |
| Skip authentication for some root fields | Root fields of listed classes do not try to authenticate. | django-graphql-jwt: `JWT_ALLOW_ANY_CLASSES`, `JWT_ALLOW_ANY_HANDLER` | missing | low | Only needed with token middleware. |

### 27. Errors and error handling

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Translated error messages | Library error messages use Django gettext and ship locales. | django-graphql-jwt: gettext messages, locales ar, de, es, fr, nl, pt_BR, zh_Hans | missing | low | No `gettext` use and no `locale` dir in `undine/`. I checked with grep. |

## saleor additions

### 1. Schema, root types and entrypoints

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Deprecated field usage tracking | Records a metric each time a deprecated or monitored field is resolved. | saleor: `monitor_fields_usage(schema)`, `BaseField(monitor_usage=True)`, metric `saleor.graphql.field.usage` | missing | medium | Helps decide when a deprecated field can be removed. Could be a lifecycle hook. |
| Extra types not reachable from roots | Registers types that no root field returns. | saleor: `build_federated_schema(..., types=[...])` | missing | low | I think `create_schema` has no `types=` argument. Not verified. |
| Version notes in descriptions | Helpers add "Added in 3.x" or "Preview feature" text to descriptions. | saleor: `ADDED_IN_3XX`, `PREVIEW_FEATURE` in `core/descriptions.py` | missing | low | Users can write it in docstrings. |

### 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Bulk error policy | Client chooses: reject all, reject failed rows, or ignore failed parts. Results are per row with errors. | saleor: `errorPolicy: ErrorPolicyEnum` (`REJECT_EVERYTHING`, `REJECT_FAILED_ROWS`, `IGNORE_FAILED`), `BulkError(path, message, code)` | missing | medium | Undine bulk mutations are all or nothing. I think. |
| Bulk size limit per mutation | Caps the number of ids or items in one bulk call. | saleor: `BULK_DELETE_LIMIT` | partial: `MUTATION_INSTANCE_LIMIT` (request-wide) | low | Request-wide cap covers most use. |
| Root mutation count limit | Caps root mutation fields per operation. | saleor: `MutationCountLimitRule`, `GRAPHQL_MUTATION_COUNT_LIMIT` | missing | medium | Undine has alias and complexity limits. No mutation count rule found with grep. |
| Reorder helper | Moves items with relative `sortOrder` moves. | saleor: `perform_reordering(qs, operations)`, `moves: [{id, sortOrder}]` | missing | low | App-specific. |
| Pydantic input validation | Validates complex inputs with a pydantic model and maps errors to codes. | saleor: `pydantic_to_validation_error` | missing | low | Also see graphene-pydantic rows. |
| Generic translate mutations | `xxxTranslate(id, languageCode, input)` mutations from translation models. | saleor: `BaseTranslateMutation` | partial: modeltranslation integration for fields | low | Saleor uses its own translation models. |

### 8. Query optimizer / database

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Read replica routing | Queries read from a replica. Mutations use the primary. | saleor: `DATABASE_CONNECTION_REPLICA_NAME`, `disallow_replica_in_context`, `@allow_writer` | missing | medium | No grep hit for replica or `.using(` in `undine/`. Django routers can do it, but not per operation type. |
| Changed-field tracking | Detects which model fields changed in a mutation. | saleor: `InstanceTracker`, `instance_tracker_fields` | missing | low | Useful for `__after__` side effects. |

### 9. DataLoaders

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Sync DataLoaders | Batching loaders that work in sync execution. | saleor: `DataLoader[K, R]` on `promise.dataloader.DataLoader` | missing | low | Inventory: no DataLoader in sync mode. Promise style is old. The optimizer covers most cases. |

### 4. Filtering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Explicit null filter semantics | `{eq: null}` on a nullable field matches nulls. | saleor: `where` inputs | partial: `isnull` lookup, `EMPTY_VALUES` skip null | low | Undine treats null as "skip filter" by default. |
| Search query syntax | One `search` argument with prefix match, OR, `-term`, quoted phrase. Results sort by rank. | saleor: root `search: String`, `RANK` sort field | partial: `PostgresFTS` filter (undocumented) | medium | Undine FTS uses raw `SearchQuery`. No rank ordering helper. I think. |
| Metadata key-value filtering | Filters on JSON metadata by key and value. | saleor: `MetadataFilterInput{key, value{eq, oneOf}}` | partial: autogenerated `JSONField` lookups | low | I think `JSONField` key lookups are not generated. Not verified. |

### 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Non-null connection edges | Connection with `edges: [Edge!]!` and `node: T!`. | saleor: `NonNullConnection` | partial: I think Undine edges and nodes are already non-null | low | Not verified. |
| Simple limit argument on nested lists | Nested list fields take `limit: Int = 100`. | saleor: `DEFAULT_NESTED_LIST_LIMIT` | partial: `OffsetPagination` on a `Field` | low | Undine needs an explicit pagination wrapper. |

### 16. Validation rules and operation limits

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Cost with list multipliers | Static cost where `first`, `last`, `limit` arguments multiply child cost. | saleor: `CostValidator`, `COST_MAP` (`complexity`, `multipliers`), `GRAPHQL_QUERY_MAX_COMPLEXITY` | partial: `MaxComplexityRule` counts database queries | medium | Inventory: no row-based cost. |
| Cost in response extensions | Returns `extensions.cost {requestedQueryCost, maximumAvailable}`. | saleor: `extensions.cost` | missing | medium | No grep hit for complexity in response extensions. |
| Federation entity count limit | Caps `_entities(representations:)` size. | saleor: `FEDERATED_QUERY_MAX_ENTITIES` | missing | medium | I did not find a limit in `undine/federation/entities.py`. |
| Block anonymous traffic switch | Rejects all anonymous requests with 401 before execution. | saleor: `Shop.allowStorefrontTraffic`, `STOREFRONT_TRAFFIC_NOT_ALLOWED` | missing | low | Django middleware can do this. |

### 17. Subscriptions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Webhooks from subscription documents | A stored subscription document defines a webhook payload. Server runs it on events and posts the result. | saleor: `webhookCreate(input: {query: ...})`, `generate_payload_from_subscription`, `webhookDryRun`, `webhookTrigger` | missing | low | Large scope. Retries, signatures, circuit breaker. |
| Subscription filter arguments | Subscription fields take arguments that filter events. | saleor: `orderCreated(channels: [String!])` | partial: function subscriptions take arguments. `SignalSubscription.filter` | low | I think model signal subscriptions have no client arguments. Not verified. |

### 22. Lifecycle hooks / Request context

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Request-scoped parameter threaded through the tree | Wraps roots so a parameter (channel, currency) reaches nested resolvers. | saleor: `ChannelContext(node, channel_slug)`, `ChannelQsContext` | missing | low | Users can store data on `info.context`. |

### 23. Apollo Federation 2

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Batched reference resolution | Resolves all representations of one type with one query. | saleor: `__resolve_references(roots, info)`, `resolve_federation_references` | missing | high | `undine/federation/entities.py` resolves each representation one by one (`_resolve_one_sync`). This is an N+1 problem. |

### 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Positive and non-negative scalars | `PositiveInt`, `NonNegativeInt`, `PositiveDecimal`. | saleor: `core/scalars.py` | missing | low | Validators can do this. |
| Image thumbnail field | Image field with `size` and `format` arguments. | saleor: `ThumbnailField(Image, size=, format=)` | missing | low | App-specific. |
| Upload validation | MIME sniffing, allowed extensions, EXIF check. | saleor: `validate_upload_file` | partial: `validate_file_upload` checks only a name. Image check with Pillow | low | Checked `undine/utils/validators.py`. |

### 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Permissions in descriptions | Adds "Requires one of: ..." to field descriptions. | saleor: `PermissionsField(auto_permission_message=True)` | missing | low | Needs declarative permissions first. |
| One-of permission sets | Passes if any of a list of permissions or auth filters match. | saleor: `one_of_permissions_or_auth_filter_required`, `AuthorizationFilters` | missing | medium | Part of the declarative permissions gap. |

### 24. Integrations / Observability

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| OpenTelemetry metrics | Metrics for operation count, duration, cost, batch size, alias count. | saleor: `saleor/graphql/metrics.py` | missing | medium | Undine OTel hook does spans only. No meter use found with grep. Inventory: no metrics integration. |
| Dataloader batch spans | Each loader batch is a span with row count. | saleor: `DataLoader` OTel span | missing | low | I think Undine field spans cover resolvers, not loader batches. |
| Introspection result cache | Caches pure introspection responses in the Django cache. | saleor: introspection cache by query hash and version | partial: `VISIBILITY_CACHE_*` per user | low | |

### 27. Errors and error handling

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Separate loggers for handled and unhandled errors | Expected errors and server faults go to different loggers. | saleor: `handled_errors_logger`, `unhandled_errors_logger` | partial: masked errors logged to `undine` logger | low | |

### 25. Tooling, typing and testing

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Test client with permission grants | Test request grants listed permissions to the user. | saleor: `ApiClient.post_graphql(..., permissions=, check_no_permissions=)` | missing | low | |

## graphene-sqlalchemy and strawberry-sqlalchemy additions

### 2. Query types and fields

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Composite primary key support | Global IDs and lookups work for models with composite keys. | strawberry-sqlalchemy: `resolve_id` joins key parts with `\|`. graphene-sqlalchemy: `resolve_id` returns a tuple string (decode missing) | missing | medium | Django 5.2 added `CompositePrimaryKey`. No grep hit for it in `undine/`. I think pk-based entrypoints and Node IDs assume one column. |
| Auto-map reachable related models | Builds empty types for related models that have no declared type. | strawberry-sqlalchemy: `mapper.finalize()` | missing | low | I think Undine needs a registered QueryType for each relation. Explicit is clearer. |
| Abstract base type for reuse | A base type class with shared hooks, not registered itself. | graphene-sqlalchemy: `Meta.abstract = True`. strawberry-sqlalchemy: type inheritance (0.6.4) | partial: I think plain QueryType subclassing works | low | Not verified. |
| Non-Django data sources | Model-backed types for another ORM. | graphene-sqlalchemy: `SQLAlchemyObjectType`. strawberry-sqlalchemy: `@mapper.type(Model)` | missing | low | Inventory: no non-Django ORM. Undine is Django-first by design. |

### 5. Ordering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Autogenerate orders only for indexed columns | Limits sortable fields to indexed or primary key columns. | graphene-sqlalchemy: `sort_enum(only_indexed=True)` | missing | medium | Protects the database from slow sorts. Undine has `exclude` and `MAX_ORDERS_PER_TYPE`. |

### 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| One shared enum per choices class | Reuses one GraphQL enum for every field that uses the same enum class. | graphene-sqlalchemy: one Graphene enum per SQL enum, cached in registry. graphene-django: notes it does not reuse | partial: `TextChoicesField` gives one enum per `TextChoices`. Plain `choices=` gives `<Model><Field>Choices` | low | |
| BigInt scalar | Separate scalar for 64-bit integers. | strawberry-sqlalchemy: `BigInt`. graphene-django: `BigIntegerField` to `BigInt` | missing | medium | GraphQL `Int` is 32-bit. `BigIntegerField` is an `IntegerField` subclass, so Undine maps it to `Int`. Large values fail to serialize. |

## graphene-pydantic additions

### 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Pydantic models as output types | Builds an object type from a Pydantic model for function fields and entrypoints. | graphene-pydantic: `PydanticObjectType` (`Meta.model`, `only_fields`, `exclude_fields`) | partial: `TypedDict` and `NamedTuple` return types | medium | No grep hit for pydantic or dataclass in `undine/converters`. Dataclass returns are likely missing too. |
| Pydantic models as input types | Builds an input object from a Pydantic model and validates the data with it. | graphene-pydantic: `PydanticInputObjectType` (validation is manual there). saleor: `pydantic_to_validation_error` | partial: `TypedDict` function arguments become input objects | medium | Automatic validation with error mapping would add value over graphene-pydantic. |
| Constraint reflection in schema | Shows field constraints like `max_length` or `gt` in the schema. | graphene-pydantic: listed as missing | missing | low | Could map to descriptions or directives. |

## graphjoiner-graphlayer additions

### 8. Query optimizer (N+1 and over-fetching)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Subquery-based child loading | Loads children with `WHERE fk IN (SELECT ... parent query)` instead of a list of parent IDs. | graphjoiner: `sql_join`, `build_query(args, parent_query, context)`. graphlayer: `gsql.join(key=..., resolve=...)` | partial: prefetches with Django `prefetch_related` (ID list) | low | I think Django prefetch always uses an ID list. Gain is small for most cases. |
| Per-request-node resolution | Runs one resolver per selection, not per row. Fewer Python calls. | graphjoiner: `fetch_immediates`. graphlayer: `@g.resolver(...)`, `graph.resolve(query)` | partial: optimizer plans queries once. Field resolvers still run per row | low | Large design change. Only Python overhead remains. |
| Flatten a to-many relation field | A field returns one sub-field of a to-many relation directly, like `bookTitles: [String]`. | graphjoiner: `extract(relationship, field_name)` | partial: `Field("rel__field")` for to-one paths | low | I think to-many lookup paths are not supported as list fields. Not verified. |

### 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| `nodes` shortcut on connections | Connection has `nodes: [T]` next to `edges`. | graphlayer: `forward_connection` (`nodes`) | missing | medium | Inventory lists this as missing. Cheap to add. |

### 15. Visibility

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Run a request against a narrower schema | Validate and introspect a request against a sub-schema given as SDL. | graphjoiner: `executor(...)(query, schema=whitelist_schema)`, `graphjoiner.schemas.parse_schema` | partial: visibility hooks per element | low | Per-client SDL allow list is a different approach. Undine visibility covers most use. |

### 1. Schema, root types and entrypoints

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Graph usable without GraphQL | Build and run typed queries from Python as an internal data layer. | graphlayer: `Root(Root.fields.books(Book.fields.title))`, `graph.resolve(query)` | missing | low | Out of scope for a GraphQL library. |
| Resolver dependency injection | Resolvers declare dependencies that the graph injects. | graphlayer: `@g.dependencies(session=...)` | missing | low | Django code uses globals and `info.context`. |
