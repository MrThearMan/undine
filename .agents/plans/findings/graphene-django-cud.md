# graphene-django-cud findings

Version checked: 0.13.1 (2026-05-16, latest on PyPI). Previous release 0.13.0 was 2024-09-03. Package `graphene-django-cud`. Import `graphene_django_cud`.
It is a mutation-only add-on for graphene-django 3 (`graphene-django>=3.0`). It has no query, filter, ordering or pagination features of its own.
Hard runtime dependencies: `graphene-file-upload` (for the `Upload` scalar), `graphene-luna` (graphql-ws subscriptions) and `gunicorn`. Python `^3.10`.
Still pre-1.0. Docs say some hook signatures will change before 1.0.0. Some doc pages are empty stubs (`ref/conversion.rst`, `ref/custom-types.rst`, `ref/mutation-lifecycle.rst`, `guide/reusing-types.rst` is "TODO").

## Mutation classes (`graphene_django_cud.mutations`)

- `DjangoCreateMutation`: argument `input`. Returns the object under `return_field_name` (default snake_case model name).
- `DjangoUpdateMutation`: arguments `id` and `input`. All included fields are required by default (full replace semantics).
- `DjangoPatchMutation`: subclass of update. All fields optional (partial update).
- `DjangoDeleteMutation`: argument `id`. Returns `found`, `deletedId`, `deletedRawId`, `deletedInputId`. `deletedId` is a Relay global ID if the model type uses a `GlobalID` id field.
- `DjangoBatchCreateMutation`: `input: [Input!]!`. Saves objects one by one (no `bulk_create`).
- `DjangoBatchUpdateMutation`, `DjangoBatchPatchMutation`: `input` list, each item has its own `id`. One `get` plus one `save` per item (no `bulk_update`).
- `DjangoBatchDeleteMutation`: `ids: [ID]!`. Returns `deletionCount`, `deletedIds`, `missedIds`.
- `DjangoFilterUpdateMutation`: arguments `filter` and `data`. `Meta.filter_fields = ("name", "house__owner__name__in")` makes a flat filter input (`house_Owner_Name_In`). Runs `queryset.filter(**filter).update(**data)`. This skips `save()`, model signals and nested relations. Returns `updatedCount`, `updatedObjects`. `field_name_mappings` is not supported here.
- `DjangoFilterDeleteMutation`: argument `input` built from `filter_fields`. Runs `queryset.delete()`. Returns `deletionCount`, `deletedIds`. Deleted IDs are always Relay global IDs.
- Every mutation needs a registered `DjangoObjectType` for the model (asserted at class creation). The output field uses that type.
- `id` arguments accept raw pks, integer strings, UUIDs and Relay global IDs. `disambiguate_id` / `disambiguate_ids` do this. Override `resolve_id(id)` / `resolve_ids(ids)` for custom ID decoding.
- No upsert mutation at top level. Upsert exists only inside nested many-to-one `auto` inputs (update if `id` exists, else create).
- No generic custom mutation base. Users write plain `graphene.Mutation` for anything else.
- No Relay `ClientIDMutation` style (`clientMutationId`) for these classes.

## Input generation (Meta options on create/update/patch/batch)

- `model`: required.
- `fields` / `exclude` (0.10.0). `only_fields` / `exclude_fields` are deprecated aliases. `fields` is applied first, then `exclude`.
- `optional_fields`, `required_fields`: force `required=False` / `required=True`. Default rules: fields with a `default`, nullable fields, and `blank=True` M2M are optional. Patch makes everything optional.
- `field_types = {"tag": graphene.Int()}`: override the generated input type of a field. Value is coerced on save, or converted by a `handle_<field>` method.
- `custom_fields = {"bark": graphene.Boolean()}`: extra input fields that are not model fields. Only available to hooks and handlers.
- `auto_context_fields = {"created_by": "user"}`: fill a model field from an `info.context` attribute. Field becomes optional. Client value overrides it.
- `field_name_mappings = {"full_name": "name"}` (0.13.0): rename model fields in the input. Also works inside all `*_extras` dicts.
- `use_id_suffixes_for_fk`, `use_id_suffixes_for_m2m` (0.13.0): rename FK inputs to `ownerId` and M2M inputs to `enemiesIds`. Global settings `GRAPHENE_DJANGO_CUD_USE_ID_SUFFIXES_FOR_FK`, `GRAPHENE_DJANGO_CUD_USE_ID_SUFFIXES_FOR_M2M`.
- `type_name`: name of the generated input type (default `<MutationName>Input`, for example `CreateUserInput`). Other mutations refer to input types by this string name.
- `return_field_name`: name of the output field.
- `ignore_primary_key=True` (create only, 0.6.5): leave the pk out of the create input.
- `login_required`, `permissions`: see Permissions.
- `use_select_for_update=True` (update/patch, 0.10.0): locks the row with `select_for_update()` inside the transaction.
- Input types are stored in a separate input registry. A `TypeMetaRegistry` stores the extras of each input type so nested use of `"CreateUserInput"` reuses its extras.
- Choice fields reuse the enum from the registered `DjangoObjectType` (0.8.0). No separate input enum.

## Model field to input mapping (`graphene_django_cud.converter.convert_django_field_to_input`)

- `singledispatch` converter, extendable with `.register(MyField)`.
- Char/Text/Email/Slug/URL/GenericIPAddress/FilePath to `String`. Integer fields to `Int`. `FloatField` to `Float`. `DecimalField` to `Decimal`. `BooleanField` to `Boolean`. `UUIDField` to `UUID`.
- `DateTimeField`, `DateField`, `TimeField` to `DateTime`, `Date`, `Time`.
- `DurationField` to custom `TimeDelta` scalar (`graphene_django_cud.types.TimeDelta`, format `HH:MM[:SS]`, hours may exceed 23).
- `JSONField`, `HStoreField` to `JSONString`. `ArrayField` to `List(inner)`. `RangeField` to list.
- `FileField`, `ImageField` to `Upload` (graphene-file-upload multipart spec). This is file upload support that graphene-django lacks.
- `AutoField`, `ForeignKey` to `ID`. `OneToOneField` / `OneToOneRel` to `ID`. `ManyToManyField`, `ManyToManyRel`, `ManyToOneRel` (reverse FK) to `[ID]`.
- Field descriptions come from `help_text`.
- Not mapped: `GenericForeignKey`, `GenericRelation`, `BinaryField`, `GeneratedField`, GeoDjango fields.

## Nested writes

- `foreign_key_extras = {"owner": {"type": "CreateUserInput" | "auto" | "ID"}}`: create the related FK object inline instead of passing an ID.
- `one_to_one_extras = {"registration": {"type": "auto"}}`: nested create for O2O. Auto type name like `CreateDogCreateRegistrationInput`.
- `many_to_one_extras = {"cats": {"exact": {...}, "add": {...}, "by_id": {"type": "ID"}, "remove": ...}}`: reverse FK operations. Each key becomes an input field (`cats`, `catsAdd`, `catsById`, `catsRemove`).
- `many_to_many_extras = {"enemies": {"exact": ..., "add": ..., "remove": {"type": "ID"} | True}}`: M2M operations.
- Operation is taken from the key name (`exact`, `add`/`append`/`create`, `remove`/`delete`, `update`/`patch`) or from an explicit `"operation"` key. `"name"` renames the input field.
- `exact` means set. For reverse FK with non-null FK it deletes related rows not in the new set. For nullable reverse FK it clears then adds. For M2M it calls `.set()`.
- `remove` on reverse FK sets the FK to `NULL` if nullable, else deletes the rows.
- `update` on many-to-one `auto` types does upsert per item by `id`.
- Nested extras can carry their own `fields`, `exclude`, `auto_context_fields`, `field_name_mappings` and deeper `*_extras`. No depth limit.
- M2M through models: docs say use `many_to_one_extras` on the through relation instead.
- Nested writes do not run the nested mutation's permissions, validation or hooks. Only the top-level `handle_<field>` / `validate_<field>` for the whole nested field.
- Related objects are fetched with `Model.objects.get(pk=...)` one by one. This bypasses custom `get_queryset` and gives one query per ID.
- Limitation (docs): a single list cannot mix IDs and objects because GraphQL unions cannot contain scalars.

## Hooks and lifecycle

- Order for create: `before_mutate` then `login_required` check then `check_permissions` then `validate` then `transaction.atomic()` with `create_obj`, `before_save`, then `after_mutate`, then the library signal.
- Order for update/patch: `before_mutate`, login check, then inside `atomic()`: `resolve_id`, `get_queryset`, optional `select_for_update`, `get`, `check_permissions(obj)`, `validate`, `update_obj`, `before_save`, `save`. Then `after_mutate` and signal.
- `before_mutate(root, info, input[, id])`: may return a changed `input`.
- `before_save(...)`: may return a changed object (or objects/queryset for batch and filter mutations).
- `after_mutate(...)`: may change `return_data`. Delete gets `(deleted_id, found)`.
- `before_create_obj(info, input, obj)` (0.12.0): runs before the first save of each created object, including nested ones.
- `after_create_obj(root, info, input, obj, full_input)` (batch create) and `after_update_obj(...)` (batch update/patch): per-item hooks.
- `get_queryset(root, info, ...)`: restrict which rows update/patch/delete/batch/filter mutations can reach. Default `Model.objects`.
- `perform_delete(obj)` on `DjangoDeleteMutation` (0.11.0): override for soft delete.
- `get_return_id(obj)` on delete and batch delete: customize returned IDs.
- `handle_<field>(cls, value, name, info)`: transform an input value before save. Disables the default FK `_id` and ID disambiguation for that field. Called for every model with a field of that name in nested writes.
- `mutate(...)` can be overridden as a last resort.
- Transactions: create, update, patch, batch create, batch update use `transaction.atomic()`. Delete, batch delete, filter delete and filter update do not wrap their work in a transaction of their own.
- No `full_clean()` or model validation call. No Django form or DRF serializer integration.

## Validation and errors

- `validate_<field>(root, info, value, input, **kwargs)`: per-field validator. Update/patch get `obj` and `id`. Batch create gets `full_input`. Raise to fail.
- `validate(root, info, input, ...)`: override for whole-input validation.
- Only top-level input keys get a validator. No nested field validators.
- Errors are raised as exceptions (top-level GraphQL `errors`). `GraphQLError("Must be logged in ...")` and `GraphQLError("Not permitted ...")`. No errors-as-data payload, no error codes, no field paths.

## Permissions and authentication

- `Meta.login_required = True`: checks `info.context.user.is_authenticated`.
- `Meta.permissions = ("app.add_model",)`: checks `user.has_perms(permissions)`. Setting permissions also turns on `login_required`.
- `get_permissions(root, info, input[, id, obj])`: return permissions dynamically. Empty list grants access.
- `check_permissions(...)`: override the whole check. Update/patch/delete pass the fetched `obj`, so object-level checks are possible by hand.
- `has_perms` is called without `obj`. No automatic object permission backend (django-guardian) support.
- No field-level permissions. No permission checks on nested related objects.
- No login, logout, JWT or session mutations.

## Signals (0.13.1, `graphene_django_cud.signals`)

- `post_create_mutation`, `post_update_mutation`, `post_delete_mutation`, `post_batch_create_mutation`, `post_batch_update_mutation`, `post_batch_delete_mutation`, `post_filter_update_mutation`, `post_filter_delete_mutation`.
- Fired once after the whole mutation, including nested relations. Unlike `post_save`, which fires before M2M and reverse relations are written.
- Docs say `sender` is the mutation class. Code sends `sender=Model`.
- No pre-mutation signals.

## Subscriptions (0.13.1, experimental)

- `DjangoCreateSubscription`, `DjangoUpdateSubscription`, `DjangoDeleteSubscription` (`graphene_django_cud.subscriptions.*`): `Meta.model`, `Meta.permissions`, `Meta.signal`, `Meta.return_field_name`.
- Default signal is Django `post_save` / `post_delete`. `GRAPHENE_DJANGO_CUD_USE_MUTATION_SIGNALS_FOR_SUBSCRIPTIONS = True` switches the default to the library mutation signals.
- `DjangoSignalSubscription`: subscribe to any Django `Signal`. `transform_signal_data(data)` maps signal kwargs to the declared graphene fields.
- `handle_object_created` / `handle_object_updated`: sync hooks to preload relations (`select_related`) before the async send. Nested fields fail otherwise because the ORM is not callable in async context.
- Fan-out is an in-process class-level dict of `asyncio.Queue`s. No channel layer, Redis or broker. Does not work across multiple processes.
- No subscription arguments or filtering (every subscriber gets every event for the model). Permission check runs once at subscribe time.
- Transport is not included. Docs point to `graphene-luna` (graphql-ws) and graphene-django docs. The test project uses `luna_ws` and `django_ws.get_websocket_application`.

## Settings

- `GRAPHENE_DJANGO_CUD_USE_ID_SUFFIXES_FOR_FK`, `GRAPHENE_DJANGO_CUD_USE_ID_SUFFIXES_FOR_M2M`, `GRAPHENE_DJANGO_CUD_USE_MUTATION_SIGNALS_FOR_SUBSCRIPTIONS`. Plain top-level Django settings, read at class creation.

## Not supported or not in scope

- No queries, filters, ordering, pagination or optimizer. Output uses graphene-django types as they are.
- No bulk SQL for batch mutations (`bulk_create` / `bulk_update` not used).
- No top-level upsert mutation. No `get_or_create`.
- No `full_clean()` model validation. No form or serializer based input.
- No errors-as-data or typed mutation errors.
- No object-level permission backend integration. No field-level permissions. No permission checks for nested writes.
- No `GenericForeignKey` nested writes.
- No async mutations. Mutations are sync only.
- No multi-process subscription broker.
- No type-hint API, no mypy plugin, no `py.typed`.

## Sources

Repo: https://github.com/tOgg1/graphene-django-cud (shallow clone at `/tmp/graphene-django-cud`, last commit 2026-05-23).

Docs read (repo `docs/` source of https://graphene-django-cud.readthedocs.io/en/latest/):
- `docs/index.rst`, `docs/guide/install.rst`, `usage.rst`, `mutations.rst`
- `docs/guide/included-and-excluded-fields.rst`, `optional-fields.rst`, `field-types.rst`, `field-mappings.rst`, `custom-fields.rst`, `naming.rst`
- `docs/guide/permissions.rst`, `validation.rst`, `custom-field-handling.rst`, `auto-context-fields.rst`, `other-hooks.rst`
- `docs/guide/nested-fields.rst`, `limitations.rst`, `reusing-types.rst` (TODO stub)
- `docs/guide/signals.rst`, `subscriptions.rst`
- `docs/ref/models/*.rst` (Meta option tables per mutation), `docs/ref/conversion.rst`, `custom-types.rst`, `mutation-lifecycle.rst` (empty stubs)

Changelog: `CHANGELOG.md` in the repo (0.0.1 to 0.13.1 plus Unreleased).

Source files checked:
- `graphene_django_cud/mutations/core.py`, `create.py`, `update.py`, `patch.py`, `delete.py`, `batch_create.py`, `batch_update.py`, `batch_delete.py`, `filter_update.py`, `filter_delete.py`
- `graphene_django_cud/converter.py`, `types.py`, `registry.py`, `consts.py`, `signals.py`, `util/__init__.py`, `util/model.py`
- `graphene_django_cud/subscriptions/core.py`, `create.py`
- `graphene_django_cud/urls.py`, `ws_urls.py`, `asgi.py`, `setup.py`, `pyproject.toml`

`/llms.txt` returned 404 at both `graphene-django-cud.readthedocs.io/llms.txt` and `/en/latest/llms.txt`. The docs site returned 200 but was not needed. PyPI JSON API used for the release dates.
