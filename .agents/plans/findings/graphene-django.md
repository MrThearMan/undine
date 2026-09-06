# graphene-django findings

Version checked: 3.2.3 (2025-03-13, latest release). Package `graphene-django`. Import `graphene_django`.
It is a Django layer on top of Graphene 3 (`graphene>=3.0,<4`, `graphql-core>=3.1`, `graphql-relay`). Anything not listed here comes from Graphene core (ObjectType, Mutation, Enum, Interface, Union, Schema, relay.Node, dataloaders via `aiodataloader`, middleware).
Python 3.8 to 3.12 in classifiers. Django 3.2 to 5.2 (`Django>=3.2,<6`, pinned in 2026-06).
Maintenance is slow. Only 4 commits after 3.2.3 (Django 5.2 support, CI, Django <6 pin). No `CHANGELOG.md`. Release notes are on GitHub releases.

## Types and fields

- `DjangoObjectType` with `class Meta: model = Model`: object type from a model. All model fields, FKs and reverse relations are generated.
- `Meta.fields = [names] | "__all__"` and `Meta.exclude = [names]`: choose fields. Setting neither gives a `DeprecationWarning`. `only_fields`/`exclude_fields` are deprecated aliases.
- `validate_fields`: warns when a `fields` name is a model attribute but not a model field, or does not exist.
- Extra fields: declare `graphene.String()` etc. on the class plus `resolve_<name>(self, info)` method. Same pattern overrides a generated field.
- `Meta.interfaces = (relay.Node,)`: makes the type a Relay node and auto-creates `<Type>Connection`.
- `Meta.connection`, `Meta.connection_class`, `Meta.use_connection`: control the auto-created connection type.
- `Meta.registry` and `Meta.skip_registry`: types register in a global `Registry` (one type per model, last wins). Relations resolve to the registered type for the related model. Related types that are not registered are silently dropped from the schema.
- `Meta.convert_choices_to_enum = False | [field names]`: turn off or limit choice-to-enum conversion per type.
- `Meta.filter_fields`, `Meta.filterset_class`: default filters for connections of this type. Both cannot be set together.
- `Meta.name`, `Meta.description`, `Meta.default_resolver`: passthrough to Graphene `ObjectType`.
- `get_queryset(cls, queryset, info)` classmethod: row-level filter for the type. Runs for `DjangoListField`, `DjangoConnectionField`, `get_node`, and FK/O2O relation fields. For FK fields with a custom `get_queryset`, each related object is fetched with its own query (N+1). Docs warn this cancels `select_related`.
- `@graphene_django.bypass_get_queryset`: resolver decorator to skip `get_queryset` for FK/O2O relation fields.
- `get_node(cls, info, id)` classmethod: single object lookup for `relay.Node.Field`. Override for per-object auth.
- `is_type_of` auto-generated. Handles proxy models.
- Proxy models and model inheritance: fields and reverse relations of base models are included (3.1.5).
- Field descriptions come from model `help_text`. Lazy translations (`gettext_lazy`) work as descriptions.
- No type description from model docstring. No field-level `deprecation_reason` from model metadata.
- `DjangoListField(Type)`: `[Type!]` list field. Uses default manager if the resolver returns `None`. Always passes through `get_queryset`.
- Plain Graphene `ObjectType` works next to model types.
- No type-hint or dataclass style API. Everything is class attributes and `Meta`.
- No mypy plugin. No `py.typed`.

## Model field mapping (`graphene_django.converter`)

- `convert_django_field` is a `functools.singledispatch`. Users call `convert_django_field.register(MyField)` for custom model fields.
- Char/Text/Email/Slug/URL/GenericIPAddress/FilePath to `String`. `FileField` and `ImageField` to `String` (file name only, no url/size type).
- Auto/BigAuto/SmallAuto to `ID`. `UUIDField` to `UUID`. `BigIntegerField` to `BigInt`. Other integer fields to `Int`.
- `BooleanField` to `Boolean`. `DecimalField` to `Decimal`. `FloatField` to `Float`. `DurationField` to `Float`.
- `DateTimeField`, `DateField`, `TimeField` to `DateTime`, `Date`, `Time`.
- `JSONField` and `HStoreField` to `JSONString` (JSON serialized as a string, not a structured scalar).
- `ArrayField` to `List(inner)`. Range fields (`RangeField`) to `List(inner)` of two items.
- FK/O2O to object field. M2M and reverse FK to `DjangoListField`, or to `DjangoConnectionField`/`DjangoFilterConnectionField` if the related type is a Relay node.
- Non-null is derived from `null=False`. Blank strings in choice fields resolve to `null`.
- Choices to enum on by default (`DJANGO_CHOICE_FIELD_ENUM_CONVERT`). Enum name is `{AppLabel}{Model}{Field}Choices`. `DJANGO_CHOICE_FIELD_ENUM_V2_NAMING` for old `{Model}{Field}` naming. `DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME` for a naming function. Choice labels become enum value descriptions. Grouped choices, callable choices and `TextChoices`/`IntegerChoices` work.
- Same enum is not reused across models with the same `TextChoices` class. Each model field gets its own enum.
- Not mapped (raises "Don't know how to convert"): `BinaryField`, `GenericForeignKey`, `GeneratedField`, GeoDjango fields. Docs point to `graphene-gis` for GeoDjango.
- No `Upload` scalar. No file upload support at all.

## Filtering (django-filter integration, optional dependency)

- `DjangoFilterConnectionField(Type, fields=, filterset_class=, extra_filter_meta=)`: connection field with filter arguments. Only works with Relay node types. There is no filterable plain list field.
- `Meta.filter_fields = [names]` (exact only) or `{"name": ["exact", "icontains"]}`: auto-generated `FilterSet`. Arguments are flat, named like `name_Icontains`.
- Custom `django_filters.FilterSet` via `filterset_class`. Full django-filter feature set (`method=`, custom filters, `request` from `info.context` for context-dependent filters).
- Filters are flat top-level arguments. No nested filter input object. No `AND`/`OR`/`NOT` composition.
- Argument types are taken from the registered `DjangoObjectType` field, else from the form field.
- `GlobalIDFilter`, `GlobalIDMultipleChoiceFilter`: auto-used for AutoField, FK, O2O, M2M and reverse filters. Filter values are Relay global IDs.
- `ListFilter`: replaces `__in` filters so input is a real GraphQL list (not CSV). Empty list returns empty result.
- `RangeFilter`: replaces `__range` filters with a two-item list input.
- `ArrayFilter`: filters for Postgres `ArrayField` (`contains`, `overlap`, `exact`).
- `TypedFilter(input_type=graphene.Boolean, method=...)`: set the GraphQL input type of a filter explicitly.
- Enum argument values are converted back to raw values before filtering.
- Invalid filter input raises `ValidationError` with the form errors as JSON in the error message.

## Ordering

- Only through django-filter `OrderingFilter` on a custom `FilterSet`. Argument is a string, e.g. `orderBy: "-created_at"`. Value is converted to snake_case.
- No ordering enum or input type. No nulls-first/last control. No ordering on nested relations beyond what `OrderingFilter` allows.

## Pagination and Relay

- `DjangoConnectionField(Type)`: Relay connection with `first`, `last`, `before`, `after` and an extra `offset` argument. `offset` cannot be combined with `before`.
- Cursors are offset-based (`arrayconnection:N`). Uses `queryset.count()` plus slicing. No keyset/cursor pagination.
- `RELAY_CONNECTION_MAX_LIMIT` (default 100) and per-field `max_limit=`: caps `first`/`last`. Exceeding it raises an error. Missing `first`/`last` defaults to the limit.
- `RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST` and per-field `enforce_first_or_last=`: require `first` or `last`.
- `DjangoConnectionField(on="manager_name")`: use a named manager instead of the default manager.
- Connection object exposes `iterable` and `length` for custom fields like `totalCount` (user must add the field on a custom `Connection` class).
- No `totalCount` built in.
- `relay.Node.Field(Type)` and `relay.Node.Field()` via Graphene. Global ID is base64 `Type:pk`. Uses `get_node`.
- `relay.ClientIDMutation` from Graphene for Relay-style mutations. Form and serializer mutations are `ClientIDMutation` subclasses (`input` argument plus `clientMutationId`).
- No offset/limit pagination for plain lists. No page-number pagination.

## Query optimization

- None. No automatic `select_related`, `prefetch_related` or `only`. Users do it by hand in resolvers.
- `get_queryset` on a related type forces one query per FK object (`converter.py` calls `get_node` per object). This was added as an auth leak fix (3.1.5). Types without a custom `get_queryset` use the normal Django attribute access.
- Community packages fill this gap (for example `graphene-django-optimizer`). Not part of graphene-django.
- Dataloaders only through Graphene core. No Django-aware dataloader helper.

## Mutations

- Plain `graphene.Mutation` with `class Arguments` and `mutate(cls, root, info, ...)`. All CUD logic is manual.
- `DjangoFormMutation` (`graphene_django.forms.mutation`): input from a Django `Form`. `Meta.form_class`, `only_fields`, `exclude_fields`. Returns form fields plus `errors: [ErrorType]`. Calls `form.save()` if it exists.
- `DjangoModelFormMutation`: input from a `ModelForm`. Adds optional `id` input for update (looked up with `_default_manager.get(pk=...)`). Returns the registered model type under `return_field_name` (default lowercased model name). `Meta.input_field_name`, `Meta.return_field_name`.
- Form mutation hooks: `get_form`, `get_form_kwargs`, `perform_mutate(form, info)`.
- `DjangoFormInputObjectType` (`graphene_django.forms.types`): input object type from a form. `Meta.form_class`, `object_type` (converts enum values back to raw choice values), `add_id_field_name`, `add_id_field_type`. For mutations using several forms.
- Form field converter `graphene_django.forms.converter.convert_form_field` (singledispatch). `ModelChoiceField` to `ID`, `ModelMultipleChoiceField` to `[ID]`. `FileField` to `String`.
- `GlobalIDFormField`, `GlobalIDMultipleChoiceField`: form fields that validate Relay global IDs.
- `SerializerMutation` (`graphene_django.rest_framework.mutation`, extra `rest_framework`): input and output from a DRF serializer. `Meta.serializer_class`, `model_class`, `model_operations = ["create", "update"]`, `lookup_field` (default pk), `only_fields`, `exclude_fields`, `convert_choices_to_enum`, `optional_fields` (undocumented, 3.1.6, `"__all__"` allowed).
- `SerializerMutation.get_serializer_kwargs(root, info, **input)`: override instance lookup. Default uses `get_object_or_404` with no permission check. `perform_mutate(serializer, info)` hook.
- Nested `ModelSerializer` and `ListSerializer` become nested input object types (`<Serializer>Input`). Nested write logic is up to the serializer.
- `write_only` fields are hidden from output. `read_only` and `HiddenField` are hidden from input.
- `ErrorType { field: String!, messages: [String!]! }`: validation errors as data in the payload. `CAMELCASE_ERRORS` camelizes field names. Code default is `True`, the docs page says `False`.
- No error `code` in `ErrorType`. No union or interface-based error result.
- `ATOMIC_MUTATIONS` (in `GRAPHENE` or per database in `DATABASES`): wrap each mutation operation in `transaction.atomic()`. Form mutation errors set a flag that rolls back. Works with `ATOMIC_REQUESTS` too (`set_rollback`).
- No delete mutation class. No bulk create/update/delete. No nested related object create/update. No `full_clean()` for plain mutations. No before/after hooks for plain mutations. Docs do not point to a CUD helper (see `graphene-django-cud` separately).

## Permissions and authentication

- No permission system. Docs show patterns only: `fields`/`exclude`, raising `PermissionDenied` in a resolver, `get_queryset`, `get_node`.
- No `IsAuthenticated`/`HasPerm` helpers. No object permission or django-guardian integration.
- Login-only API: subclass `GraphQLView` with `LoginRequiredMixin`.
- `info.context` is the Django `HttpRequest`. `request.user` is available.
- No login, logout or register mutations. No JWT. Community `django-graphql-jwt` is the usual choice.

## Serving and transport

- `GraphQLView` (`graphene_django.views`): sync Django view. GET and POST. Content types `application/json`, `application/graphql`, form-urlencoded, multipart (no file map handling).
- `GraphQLView.as_view(schema=, graphiql=, middleware=, root_value=, pretty=, batch=, subscription_path=, execution_context_class=, validation_rules=)`.
- `batch=True`: array of operations in one request. Response entries include `id` and `status`. Cannot be combined with `graphiql`.
- Overridable hooks: `get_context(request)`, `get_root_value(request)`, `get_middleware(request)`, `format_error(error)`, `json_encode`, `parse_body`, `execute_graphql_request`.
- Mutations over GET are refused with 405. Errors without a path give status 400.
- `?pretty` query param or `pretty=True` for indented JSON. `?raw` to skip GraphiQL.
- `ensure_csrf_cookie` on dispatch. Docs say to wrap with `csrf_exempt` for API clients.
- No async view. No `AsyncGraphQLView`. Async resolvers are not executed by `GraphQLView` (it calls sync `execute`).
- GraphiQL 2.4.7 from CDN with SRI hashes and the GraphiQL Explorer plugin (3.1.1). Settings `GRAPHIQL_HEADER_EDITOR_ENABLED`, `GRAPHIQL_SHOULD_PERSIST_HEADERS`, `GRAPHIQL_INPUT_VALUE_DEPRECATION`. Template `graphene/graphiql.html` is overridable via `graphiql_template`.
- `validation_rules=(DisableIntrospection,)` etc. on the view (3.2.0). `MAX_VALIDATION_ERRORS` setting. Graphene core has `depth_limit_validator` and `DisableIntrospection`.
- `MIDDLEWARE` setting: tuple of Graphene middleware import paths.
- No persisted queries. No `@defer`/`@stream`. No GraphQL over SSE. No APQ. No response caching.

## Subscriptions

- Not supported. Docs point to third-party packages (`graphql-ws`, `django-channels-graphql-ws`, `graphene-subscriptions`) over Channels.
- `SUBSCRIPTION_PATH` setting only tells GraphiQL where the websocket endpoint is. GraphiQL uses `subscriptions-transport-ws` (old protocol).

## Schema export

- `manage.py graphql_schema --schema path.schema --out schema.json|schema.graphql --indent N --watch`. `--out -` prints to stdout.
- JSON output is sorted introspection. `.graphql` output is SDL.
- Settings `SCHEMA`, `SCHEMA_OUTPUT`, `SCHEMA_INDENT` supply defaults.

## Testing and debugging

- `graphene_django.utils.testing.GraphQLTestCase` and `GraphQLTransactionTestCase`: `self.query(query, operation_name=, input_data=, variables=, headers=)`, `assertResponseNoErrors`, `assertResponseHasErrors`. Returns the raw `HttpResponse`.
- `GRAPHQL_URL` class attribute or `TESTING_ENDPOINT` setting (default `/graphql`).
- `graphql_query(query, ..., client=, graphql_url=)`: function for pytest fixtures.
- `input_data=` sets the `$input` variable as a shortcut.
- No query-count assertion helpers.
- `DjangoDebugMiddleware` plus `graphene.Field(DjangoDebug, name="_debug")` on `Query`: returns executed SQL (`sql { rawSql, duration, isSlow, params, vendor, alias, ... }`) and `exceptions { excType, message, stack }` in the response. Must be the last field in the query.
- `DjangoDebugMiddleware` is added to `MIDDLEWARE` by default when `settings.DEBUG` is `True`.
- No django-debug-toolbar integration.

## Settings (`GRAPHENE` dict)

- `SCHEMA`, `SCHEMA_OUTPUT`, `SCHEMA_INDENT`, `MIDDLEWARE`, `RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST`, `RELAY_CONNECTION_MAX_LIMIT`, `CAMELCASE_ERRORS`, `DJANGO_CHOICE_FIELD_ENUM_CONVERT`, `DJANGO_CHOICE_FIELD_ENUM_V2_NAMING`, `DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME`, `SUBSCRIPTION_PATH`, `GRAPHIQL_HEADER_EDITOR_ENABLED`, `GRAPHIQL_SHOULD_PERSIST_HEADERS`, `GRAPHIQL_INPUT_VALUE_DEPRECATION`, `ATOMIC_MUTATIONS`, `TESTING_ENDPOINT`, `MAX_VALIDATION_ERRORS`.
- Settings reload on Django `setting_changed` signal (DRF-style settings object).

## Not supported or not in scope

- No query optimizer.
- No permission or auth helpers.
- No async view or async ORM support.
- No subscriptions.
- No file uploads.
- No nested filter inputs or logical filter operators. No filtering on plain lists.
- No ordering input type.
- No keyset pagination. No `totalCount`.
- No generic CUD mutations, bulk mutations, or nested mutations. Only form and DRF serializer mutations.
- No federation support in graphene-django (Graphene has `graphene-federation` as a separate package).
- No aggregation, annotation or computed-field helpers.
- No `GenericForeignKey`, `BinaryField`, GeoDjango mapping.
- No persisted queries, `@defer`, `@stream`, `@oneOf`.
- No query cost or complexity limit of its own. Only validation rules passed to the view.
- No mypy plugin or type-hint based API.
- No i18n/modeltranslation integration beyond lazy descriptions.

## Sources

Repo: https://github.com/graphql-python/graphene-django (shallow clone at `/tmp/graphene-django`, main branch, last commit 2026-06-24).

Docs read (repo `docs/` source of https://docs.graphene-python.org/projects/django/en/latest/):
- `docs/index.rst`, `installation.rst`, `settings.rst`, `schema.rst`
- `docs/queries.rst` (https://docs.graphene-python.org/projects/django/en/latest/queries/)
- `docs/fields.rst`, `extra-types.rst`
- `docs/filtering.rst` (https://docs.graphene-python.org/projects/django/en/latest/filtering/)
- `docs/mutations.rst` (https://docs.graphene-python.org/projects/django/en/latest/mutations/)
- `docs/authorization.rst`, `subscriptions.rst`, `validation.rst`, `introspection.rst`, `debug.rst`, `testing.rst`
- `docs/tutorial-plain.rst`, `tutorial-relay.rst` (skimmed, basic tutorials)

Changelog: no `CHANGELOG.md` in the repo. Read GitHub releases v3.0.0 to v3.2.3 (https://github.com/graphql-python/graphene-django/releases) and the compare `v3.2.3...main`.

Source files checked for undocumented features:
- `graphene_django/__init__.py`, `types.py`, `converter.py`, `fields.py`, `registry.py`, `settings.py`, `views.py`, `compat.py`, `utils/utils.py`, `utils/testing.py`
- `graphene_django/filter/fields.py`, `filter/utils.py`, `filter/filterset.py`, `filter/filters/*.py`
- `graphene_django/forms/mutation.py`, `forms/types.py`, `forms/forms.py`, `forms/converter.py`
- `graphene_django/rest_framework/mutation.py`, `rest_framework/serializer_converter.py`
- `graphene_django/debug/middleware.py`, `debug/sql/types.py`, `debug/exception/types.py`
- `graphene_django/management/commands/graphql_schema.py`
- `setup.py`

`/llms.txt` returned 404 on both `docs.graphene-python.org` and the Django project path. The docs site returned 200 but was not needed because the docs source is in the repo.
