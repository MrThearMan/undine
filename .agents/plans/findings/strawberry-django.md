# strawberry-django findings

Version checked: 0.90.0 (2026-09-26). Package `strawberry-graphql-django`. Import `strawberry_django`.
It is a Django layer on top of Strawberry. Anything not listed here comes from Strawberry core (schema, extensions, directives, dataloaders, subscriptions, file uploads, views).
Python 3.10 to 3.14. Django 5.x and 6.0 (4.2 dropped in 0.83.0). graphql-core 3.2 and 3.3.

## Types and fields

- `@strawberry_django.type(Model)`: object type from a model. Fields are opt-in via annotations with `strawberry.auto`.
- `type(..., fields="__all__" | [names], exclude=[names])`: auto-populate fields from the model. `fields` wins over `exclude`.
- `@strawberry_django.interface(Model)`: model-backed interface. Used for polymorphism.
- `@strawberry_django.input(Model)` and `@strawberry_django.partial(Model)` (or `input(..., partial=True)`): input types from models. Partial makes only `auto` fields optional.
- `type(..., field_cls=MyField)`: replace the field class for all fields on a type. Subclass `StrawberryDjangoField` to change behavior.
- `type(..., filters=, order=, ordering=, pagination=True)`: default filter, order and pagination for every list field of that type.
- `type(..., only=, select_related=, prefetch_related=, annotate=, disable_optimization=)`: type-level optimizer hints.
- `type(..., directives=, extend=, description=, name=)`: passthrough to Strawberry.
- `get_queryset(cls, queryset, info, **kwargs)` classmethod on a type: filters every queryset for that type. Runs once per queryset (tracked via `StrawberryDjangoQuerySetConfig`). Used for row-level visibility.
- `is_type_of` auto-generated on types. User `is_type_of` in superclasses is kept (0.86.4).
- `strawberry_django.field(...)`: field with `field_name=`, `filters=`, `order=`, `ordering=`, `pagination=`, `description=`, `extensions=`, `permission_classes=`, and optimizer hints.
- `field(field_name="a__b__c")`: flatten relations with Django `__` traversal. Returns `None` if any step is `None`. Optimizer infers `select_related`/`only` (0.75.0).
- `field(annotate={"name": Count(...)})` or `annotate=lambda info: ...`: computed field from ORM annotation.
- `@strawberry_django.field` on a method: custom resolver. Sync resolvers are auto-wrapped in `sync_to_async` under ASGI (`django_resolver`).
- Overriding a resolver removes automatic filters/order/pagination. Re-apply with `strawberry_django.filters.apply(...)` and `strawberry_django.ordering.apply(...)`.
- `strawberry_django.argument(...)`: helper for declaring arguments.
- `model_property` / `model_cached_property` (`strawberry_django.descriptors`): model `@property` with optimizer hints. Resolvable with `auto`.
- `FIELD_DESCRIPTION_FROM_HELP_TEXT` and `TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING` settings: descriptions from Django metadata. Off by default.
- Single-object root field `fruit: Fruit = strawberry_django.field()` gets a required `pk` argument automatically. Needs the root type to be named `Query`.
- `strawberry_django.export_schema` management command: `python manage.py export_schema app.schema --path out.graphql`.
- Mypy plugin: not provided. Package has `py.typed` and typed overloads.

## Model field mapping (`strawberry_django.fields.types`)

- `field_type_map`, `input_field_type_map`, `relay_field_type_map`, `relay_input_field_type_map`: global dicts. Users `update()` them for custom model fields.
- Scalars: Auto/BigAuto/SmallAuto to `ID`, char/text/email/slug/url/IP to `str`, ints, `bool`, `float`, `Decimal`, `date`, `datetime`, `time`, `UUID`, `JSONField` to `JSON`.
- `FileField` to `DjangoFileType` (name, path, size, url). `ImageField` to `DjangoImageType` (+ width, height). Input side maps both to `Upload`.
- `ArrayField` auto-mapped to list (Postgres). `GeneratedField` resolved from its output field.
- Relations: FK/O2O to object, M2M and reverse to list. Without a declared type they map to `DjangoModelType { pk }`.
- `_id` FK attnames (e.g. `color_id: auto`) map to `ID` and work in create inputs (fixed 0.79.1).
- GeoDjango: `Point`, `LineString`, `LinearRing`, `Polygon`, `MultiPoint`, `MultiLineString`, `MultiPolygon` scalars as coordinate arrays. `Geometry` scalar accepts WKT/EWKT/HEXEWKB/GeoJSON input but outputs coordinates.
- Enums: `GENERATE_ENUMS_FROM_CHOICES` setting makes enums from `choices`. Recommended path is `django-choices-field` (`TextChoicesField`, `IntegerChoicesField`) for enum from `TextChoices`/`IntegerChoices`.
- `MAP_AUTO_ID_AS_GLOBAL_ID` setting: `auto` id fields become `relay.GlobalID`.
- Not auto-mapped: `DurationField`, `BinaryField`, `HStoreField`, range fields, `GenericForeignKey`. Users must declare the type or extend `field_type_map`.

## Filtering

- `@strawberry_django.filter_type(Model, lookups=True)`: filter input. Renamed from `filter` (still works with `DeprecationWarning`).
- Every filter input gets `AND`, `OR`, `NOT` (single object, or `list[Self]` when declared) and `DISTINCT: Boolean`. Logical fields are evaluated last.
- Without `lookups=True`, fields are exact match. With it, each field gets a typed lookup input.
- Lookup types (importable from `strawberry_django`): `BaseFilterLookup` (exact, isNull, inList), `ComparisonFilterLookup` (+ gt, gte, lt, lte, range), `RangeLookup`, `FilterLookup`/`StrFilterLookup` (+ iExact, contains, iContains, startsWith, iStartsWith, endsWith, iEndsWith, regex, iRegex), `DateFilterLookup` (+ year, month, day, weekDay, isoWeekDay, week, isoYear, quarter), `TimeFilterLookup` (+ hour, minute, second, date, time), `DatetimeFilterLookup`, `GeometryFilterLookup` (contains, disjoint, equals, intersects, overlaps, touches, within) (0.90.0).
- UUID fields get string lookups. Enum fields get `inList`.
- Docs warn that `regex`/`iRegex` are a ReDoS risk. No built-in switch to remove them. Users subclass the lookup.
- Nested relation filters: annotate a field with another filter type (`color: ColorFilter | None`).
- `@strawberry_django.filter_field` method: custom filter. Args `self, value, prefix, queryset, info`. Returns `Q` or `(QuerySet, Q)`. Can `alias()`/`annotate()` the queryset.
- Method named `filter` overrides filtering for the whole object. Use `strawberry_django.process_filters(..., skip_object_filter_method=True)` for default behavior.
- `filter_field(filter_none=True)`: by default `null` values are ignored and custom methods are not called. So `exact: null` does not filter by null. `isNull` is needed.
- `filter_field(resolve_value=True|False|UNSET)`: controls unwrapping of `GlobalID` to node id, enums to values, `Maybe`/`Some`.
- `filter_field(skip_queryset_filter=True)`: virtual parameter field used only by a custom `filter` method (0.78.0).
- Filters on a type are inherited by fields and by update/delete mutations. Field-level `filters=` overrides.
- `USE_DEPRECATED_FILTERS` setting: legacy filter API for migration.
- No aggregation filters (e.g. `count > n`) built in. Done with custom `filter_field` + `alias`.
- No full-text search lookup built in.

## Ordering

- `@strawberry_django.order_type(Model)`: new ordering input. Inputs are `@oneOf`. Clients pass a list: `ordering: [{name: ASC}, {created: DESC}]`. Field argument name is `ordering`.
- `Ordering` enum: `ASC`, `DESC`, `ASC_NULLS_FIRST`, `ASC_NULLS_LAST`, `DESC_NULLS_FIRST`, `DESC_NULLS_LAST`. `Ordering.resolve(name)` builds `F().asc/desc(nulls_...)`.
- Nested ordering across relations (`color: ColorOrder | None`).
- `@strawberry_django.order_field` method: custom ordering. Returns list of `F`/str, or `(QuerySet, list)`. `order_none=True` to not ignore null.
- Method named `order` overrides the whole object. Use `strawberry_django.ordering.process_ordering_default`.
- Legacy `@strawberry_django.order` (argument `order`, object keys define priority, `sequence` param, `process_order`). Deprecated but can coexist. Clients use one or the other.
- Unordered querysets are ordered by pk automatically for deterministic pagination.

## Pagination

- `pagination=True` on type or field: adds `pagination: OffsetPaginationInput { offset: Int! = 0, limit: Int }` to list fields.
- `PAGINATION_DEFAULT_LIMIT` (default 100, `None` for unlimited) and `PAGINATION_MAX_LIMIT` (default 100 since 0.85.0, caps `limit: null` too).
- Per-field defaults via a subclass of `OffsetPaginationInput` passed as `pagination=MyInput`.
- `OffsetPaginated[T]` + `strawberry_django.offset_paginated()`: wrapper type with `totalCount`, `pageInfo { limit, offset }`, `results`. `pageInfo.limit` is the applied limit.
- `OffsetPaginated` is subclassable. Extra fields can use `self.queryset`, `self.pagination`, `get_total_count()`, `get_paginated_queryset()`, `resolve_paginated(...)` classmethod.
- `@strawberry_django.offset_paginated(OffsetPaginated[T], order=...)` on a method: custom base queryset with extra arguments.
- Nested paginated lists and connections are prefetched with a window function (`_PaginationWindow`, `apply_window_pagination`). This avoids N+1 for per-parent pagination.
- No page-number pagination type. No keyset pagination outside relay.

## Relay

- Uses Strawberry `relay.Node`, `relay.GlobalID`, `relay.NodeID`. Node id resolved from model pk automatically.
- `strawberry_django.node()`: single node field with Django optimizations.
- `strawberry_django.connection()`: connection field. Integrates filters, ordering, permissions, optimizer.
- `strawberry.relay.ListConnection`: offset slicing. `DjangoListConnection`: same plus `totalCount` (was `ListConnectionWithTotalCount`).
- `DjangoCursorConnection`: true keyset cursors using range `Q` filters on the order fields. Adds pk as tiebreaker. Cursors not portable across different orderings.
- `connection(max_results=N)`: per-connection cap.
- Custom kwargs forwarded to connection resolvers. Resolvers may return `QuerySet[Model]` (0.86.3).
- `resolve_model_nodes`, `resolve_model_node`, `resolve_model_id` in `strawberry_django.relay.utils`. Run type `get_queryset`.
- Nested connections optimized by prefetch, including `totalCount` (0.86.6).
- `NodeInput`, `NodeInputPartial`: inputs with `id: GlobalID` for update/delete.

## Query optimizer

- `DjangoOptimizerExtension` schema extension. Applies `only()`, `select_related()`, `prefetch_related()` (with `Prefetch` querysets), `annotate()` based on the selection set.
- Constructor flags: `enable_only_optimization`, `enable_select_related_optimization`, `enable_prefetch_related_optimization`, `enable_annotate_optimization`, `enable_nested_relations_prefetch`, `prefetch_custom_queryset` (use default manager instead of base manager).
- Field hints: `only`, `select_related`, `prefetch_related` (strings or `Callable[[Info], Prefetch]`), `annotate` (expression or `Callable[[Info], Expression]`), `disable_optimization=True`.
- Nested relations with filters/order/pagination are prefetched with those applied.
- Aliased duplicate selections are merged into one prefetch (0.76.1).
- FK fields auto-injected into `.only()` of user `Prefetch` querysets (0.77.0).
- FK with nested annotations switches to `prefetch_related` instead of join.
- `only()` is turned off for mutations.
- `strawberry_django.optimizer.optimize(qs, info, config=, store=)`: manual optimization call inside a resolver. `OptimizerConfig`, `OptimizerStore` are public.
- `DjangoOptimizerExtension.disabled()`: context manager to turn it off.
- Polymorphism: optimizes interfaces. Supports django-polymorphic, django-model-utils `InheritanceManager` (auto `select_subclasses`), and custom `resolve_type` on a single-table model.
- Does not merge unrelated root fields into one query. It is a per-root-field optimizer.
- No query cost or complexity analysis of its own. Docs point to Strawberry `QueryDepthLimiter`.

## Mutations

- `@strawberry_django.mutation`: like `strawberry.mutation`, but async-safe and integrated with permissions.
- `@strawberry_django.input_mutation`: wraps args into a single generated `input` type (Strawberry `InputMutationExtension`).
- `handle_django_errors=True` (or `MUTATIONS_DEFAULT_HANDLE_ERRORS`): return type becomes `union XPayload = X | OperationInfo`. Catches `ValidationError`, `PermissionDenied`, `ObjectDoesNotExist`.
- `OperationInfo { messages: [OperationMessage!]! }`, `OperationMessage { kind, message, field, code }`, `OperationMessageKind` enum (INFO, WARNING, ERROR, PERMISSION, VALIDATION). Dict `ValidationError` maps to `field`. `code` from `ValidationError.code`.
- Error-handling mutations can return interfaces, expanded to concrete types in the union (0.88.0).
- CUD factories: `strawberry_django.mutations.create(Input)`, `update(PartialInput)`, `delete(Input)`. Each runs in `transaction.atomic`.
- Batch CUD: `create(list[Input])`, `update(list[Input])`, `delete(list[Input])` in one transaction.
- Filtered bulk update/delete: `update(Input, filters=F)`, `delete(filters=F)`. Refused without filters unless `ALLOW_MUTATIONS_WITHOUT_FILTERS=True`.
- `argument_name=` (default `data`, or `MUTATIONS_DEFAULT_ARGUMENT_NAME`).
- `key_attr=` (or `DEFAULT_PK_FIELD_NAME`): look up by a unique field instead of pk.
- `full_clean=True|False|FullCleanOptions(exclude=, validate_unique=, validate_constraints=)`: model `full_clean()` before save. On by default.
- Relation inputs: `OneToOneInput { set }`, `OneToManyInput { set }`, `ManyToOneInput`/`ManyToManyInput { add, remove, set }`, generic `ListInput[T] { set, add, remove }`. `through_defaults` key passes data to the M2M through model.
- Nested create/update of related objects inside `ListInput[SomePartialInput]`, multi-level, with `full_clean()` on each (0.47+).
- `strawberry.Maybe[T]` / `Maybe[T | None]` supported in inputs to tell "absent" from "null".
- `strawberry_django.mutations.resolvers.create/update/delete/update_m2m/parse_input`: reusable helpers for custom mutations.
- No mutation hooks (before/after save, per-field clean) in the core. Docs point to `strawberry-django-extras` for hooks and deep nested CUD.
- No Django Form or DRF serializer driven mutations. Docs show manual `ModelForm` use in a resolver.
- No built-in "get or create", "upsert" or bulk-create-with-`bulk_create` mutation.

## Permissions

- Field extensions in `strawberry_django.permissions`: `IsAuthenticated`, `IsStaff`, `IsSuperuser`, `HasPerm`, `HasSourcePerm`, `HasRetvalPerm`.
- `HasPerm(perms, any_perm=True, with_anonymous=True, with_superuser=False, message=, fail_silently=True, use_directives=True)`.
- `HasSourcePerm`: object permission on the parent object. `HasRetvalPerm`: object permission on the returned value.
- `HasRetvalPerm` on a list field filters the queryset in SQL via `filter_for_user` (user perms, group perms, and guardian object perms tables). Evaluated lists are filtered in Python.
- Failure fallback order: `OperationInfo` if in the return union, `null` if nullable, empty list, empty connection, else `PermissionDenied`.
- Custom checks: subclass `DjangoPermissionExtension` and implement `resolve_for_user`. Raise `DjangoNoPermission`.
- Permission extensions add schema directives to the SDL by default (visible in introspection). `use_directives=False` to hide.
- Helpers: `filter_with_perms(qs, info)`, `get_with_perms(pk, info, ...)`, `strawberry_django.utils.query.filter_for_user(qs, user, perms, ...)`.
- django-guardian integration (`strawberry_django.integrations.guardian`) for object permissions.
- No input-field level permission on mutation inputs. No permission checks on filter or order inputs.
- Strawberry `permission_classes=[BasePermission]` also work.

## Authentication

- `strawberry_django.auth.current_user()`, `login()`, `logout()`, `register(UserInput)`.
- Session based. Works with WSGI, ASGI and Channels websockets (uses `channels.auth.login` there).
- `register` runs `validate_password` and `set_password`.
- `get_current_user(info, strict=)`, `aget_current_user(...)` in `strawberry_django.auth.utils`.
- No JWT or token auth. Docs point to `strawberry-django-auth` and `strawberry-django-extras`.
- No password reset, email verification or change password mutations.

## Serving, subscriptions and transport

- Views are Strawberry's: `strawberry.django.views.GraphQLView` and `AsyncGraphQLView`. GraphiQL included.
- `strawberry_django.routers.AuthGraphQLProtocolTypeRouter(schema, django_application=, url_pattern="^graphql")`: Channels router for HTTP + websocket with `AuthMiddlewareStack` and `AllowedHostsOriginValidator`.
- Subscriptions: plain Strawberry async generator subscriptions over Channels. No model-signal based subscriptions. No built-in broadcast helper beyond Channels layers.
- File uploads via Strawberry `Upload` (multipart spec).
- No persisted queries, no `@defer`/`@stream` of its own. These depend on Strawberry core.

## Caching and performance extensions

- `DjangoValidationCache(cache_name=, timeout=, hash_fn=)`: caches GraphQL document validation in the Django cache.
- `DjangoCacheBase`: base extension to build other Django-cache-backed extensions.
- No response caching, no per-field caching.

## Federation

- `strawberry_django.federation.type(Model, keys=[...], extend=, shareable=, inaccessible=, authenticated=, policy=, requires_scopes=, tags=)`: auto-generates `resolve_reference` using the model and optimizer (0.76.0).
- `strawberry_django.federation.interface(...)` and `strawberry_django.federation.field(external=, requires=, provides=, override=, shareable=, ...)`.
- Composite keys via space-separated strings. Multiple keys create multiple `@key` directives.
- Requires `strawberry.federation.Schema`.

## Testing and debugging

- `strawberry_django.test.client.TestClient(path, client=None)` and `AsyncTestClient`. `query(query, variables=, headers=, files=, assert_no_errors=True)` returns `Response(errors, data, extensions)`. `with client.login(user):` context manager.
- `strawberry_django.middlewares.debug_toolbar.DebugToolbarMiddleware`: django-debug-toolbar panel for GraphiQL requests. Compatible with debug-toolbar 7.
- No query-count assertion helpers.

## Not supported or not in scope

- No schema-first or SDL-driven mode.
- No built-in query complexity or cost limit. No rate limiting.
- No aggregation types (count, sum, avg, group-by) as generated schema. Only per-field `annotate=`.
- No generic relation (`GenericForeignKey`) auto mapping.
- No built-in translation or i18n of fields (e.g. modeltranslation).
- No built-in soft delete, audit log or history integration.
- No directive-based permissions defined in SDL. Directives are only emitted for documentation.
- No mutation middleware or hook system in core.
- No Django admin-like auto CRUD schema generation. Every type and mutation is declared by hand.
- No mypy plugin.

## Sources

Repo: https://github.com/strawberry-graphql/strawberry-django (shallow clone at `/tmp/strawberry-django`, main branch, 2026-09-27).

Docs read (repo `docs/` source of https://strawberry.rocks/docs/django):
- `docs/index.md` (https://strawberry.rocks/docs/django)
- `docs/guide/types.md`, `fields.md`, `queries.md`, `resolvers.md`, `settings.md`, `model-properties.md`
- `docs/guide/filters.md`, `ordering.md`, `legacy-ordering.md`, `pagination.md`, `relay.md`
- `docs/guide/optimizer.md`, `performance.md`, `dataloaders.md`
- `docs/guide/mutations.md`, `nested-mutations.md`, `validation.md`, `error-handling.md`
- `docs/guide/permissions.md`, `authentication.md`, `subscriptions.md`, `views.md`, `export-schema.md`, `unit-testing.md`, `troubleshooting.md`
- `docs/faq.md`, `docs/community-projects.md`
- `docs/integrations/channels.md`, `choices-field.md`, `debug-toolbar.md`, `federation.md`, `geodjango.md`, `guardian.md`

Changelog: `CHANGELOG.md` in the repo (0.3 to 0.90.0).

Source files checked for undocumented features:
- `strawberry_django/__init__.py`, `type.py`, `fields/types.py`, `fields/field.py`
- `strawberry_django/optimizer.py`, `pagination.py`, `queryset.py`, `resolvers.py`
- `strawberry_django/mutations/mutations.py`, `mutations/fields.py`, `mutations/resolvers.py`
- `strawberry_django/permissions.py`, `utils/query.py`, `auth/utils.py`
- `strawberry_django/extensions/django_cache_base.py`, `relay/utils.py`

`https://strawberry.rocks/llms.txt` returned 404. Docs site page returned 200 but was not needed because the docs source is in the repo.
