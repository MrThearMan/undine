# Graphene findings

Version checked: 3.4.3 (PyPI, 2024-11-09, latest release). Last commit on `master`: 2024-11-09 (the 3.4.3 release commit). No commits in the 22 months after that.
Package `graphene`. Import `graphene`. Depends on `graphql-core>=3.1,<3.3`, `graphql-relay>=3.1,<3.3`, `python-dateutil`, `typing-extensions`. Python 3.8 to 3.13.
Core library only. Not tied to any web framework or ORM. No HTTP view, no GraphiQL, no settings. Integrations are separate packages: `graphene-django`, `graphene-sqlalchemy`, `graphene-mongo`, `graphene-federation`, `graphene-file-upload`. Flask, Starlette and FastAPI are listed as integrations in the docs.
This is the Graphene 3 code-first API that graphene-django builds on. The Django details are in `graphene-django.md`.
No `CHANGELOG.md`. Release notes are on GitHub releases. `UPGRADE-v1.0.md` and `UPGRADE-v2.0.md` are in the repo. v3 upgrade notes are on the GitHub wiki.

## API style (the class-and-Meta pattern)

- Every type is a Python class. Class attributes become fields. Options go in an inner `class Meta` (or a `dict`) or as class keyword arguments (`__init_subclass_with_meta__`).
- `Meta.abstract = True`: base class that is not a schema type. Only `abstract` is allowed in that Meta.
- `Meta.name`, `Meta.description` on all named types. Description defaults to the class docstring (`trim_docstring`).
- Field order comes from a global creation counter (`OrderedType`). Fields keep definition order.
- Unmounted vs mounted types: `graphene.String()` on an `ObjectType` is mounted as a `Field`. The same in `Field(...)` kwargs is an `Argument`. On an `InputObjectType` it is an `InputField`. Explicit forms: `Field(String)`, `Argument(String)`, `InputField(String)`. Helpers: `String().Field()`, `.Argument()`, `.InputField()`.
- Field types can be a class, a lambda (`lambda: Person`), a dotted import string (`"app.types.Person"`), or `graphene.lazy_import("app.types", "Person")`. This solves circular imports.
- `graphene.Dynamic(lambda: Field(...), with_schema=False)`: field type decided when the schema is built. Returning `None` drops the field. Integrations use this for relations to types that may not exist.
- Types are classes, not type hints. No type-annotation or dataclass-style definition. No `py.typed`. No mypy plugin. `mypy.ini` exists only for the library itself.
- `BaseType.create_type(class_name, **options)`: build a type class at runtime.
- `Schema.lazy(name)` and `schema.<TypeName>` attribute access: look up a type in a built schema.

## Object types and fields

- `graphene.ObjectType`: fields from class attributes. Inherits fields from Python base classes through the MRO.
- `ObjectType` instances are value objects. The metaclass makes a dataclass-like `__init__`, `__eq__`, `__repr__` from the fields. `Person(first_name="Bob")`.
- Resolvers: `resolve_<field>(parent, info, **args)` methods. They are implicit static methods. The first argument is the parent value, never `self`.
- `Field(resolver=func)`: resolver from outside the class. `Field(source="attr")`: read another attribute of the parent. If that attribute is a method it is called.
- Resolvers defined on an `Interface` are used by implementing types that do not define their own (`get_function_for_type`).
- Default resolver: `dict_or_attr_resolver`. Dict key lookup for dicts, `getattr` for others. Uses `Field.default_value` as the fallback.
- `Meta.default_resolver` per type. `graphene.types.resolver.set_default_resolver(fn)` globally. Also `attr_resolver` and `dict_resolver`.
- `Field(type_, args=None, resolver=None, source=None, deprecation_reason=None, name=None, description=None, required=False, default_value=None, **extra_args)`.
- `Field(args={"description": String()})`: define arguments whose names clash with `Field` keyword names.
- `required=True` wraps in `NonNull`. `graphene.NonNull(T)` and `graphene.List(T)` for explicit structures.
- `deprecation_reason=` on fields, arguments, input fields (since 3.2.1) and enum values. Required arguments cannot be deprecated (asserted).
- `Meta.possible_types = (PyClass,)`: `isinstance` check used for `is_type_of`. Or an `is_type_of(cls, root, info)` classmethod. Both together is an error.
- `Meta.fields = {name: Field}`: dict of fields instead of attributes. Docs say not recommended.
- Field subclasses can override `wrap_resolve(parent_resolver)` and `wrap_subscribe(parent_subscribe)`. This is the extension point used by `ConnectionField`, `GlobalID` and integrations. `get_resolver` is the deprecated name.
- `@graphene.resolve_only_args`: deprecated decorator that drops `info` from resolvers.
- No field-level permission hooks. No field-level complexity or cost. No field middleware per field. No visibility or schema hiding.
- No computed fields from model metadata. No automatic field generation from any data source (that is the job of integrations).

## Arguments

- Arguments are kwargs of `Field` or of a mounted scalar (`String(first_name=String())`). `Argument(type_, default_value=Undefined, deprecation_reason=None, description=None, name=None, required=False)`.
- Arguments not sent by the client are not passed to the resolver at all. Resolvers must use `**kwargs` or Python defaults. This lets code tell "not given" from `null`.
- Argument `default_value` is shown in the schema.
- No argument validation hooks. No input coercion hooks beyond scalars.

## Input object types

- `graphene.InputObjectType`: fields become `InputField`. Nesting input types is allowed.
- Values arrive as an `InputObjectTypeContainer` (a `dict` subclass with attribute access). `Meta.container` sets a custom container class.
- Unset optional fields read as `None` by attribute access. `graphene.types.inputobjecttype.set_input_object_type_default_value(graphql.Undefined)` switches this to `Undefined` globally (3.3.0). Release notes say `Undefined` will become the default in the future.
- `InputField(type_, name=None, default_value=Undefined, deprecation_reason=None, description=None, required=False)`.
- No `@oneOf` input objects. No input validators. No input-to-model mapping.

## Mutations

- `graphene.Mutation`: `class Arguments` for inputs, class attributes for output fields, `mutate(parent, info, **args)` method. Mount with `CreatePerson.Field(name=, description=, deprecation_reason=, required=)`.
- `Output = SomeObjectType` (or `Meta.output`): return an existing type instead of a mutation-specific payload type.
- `Meta.resolver`, `Meta.arguments`, `Meta.interfaces` for the payload type.
- `class Input` on a plain `Mutation` is deprecated (use `Arguments`).
- `relay.ClientIDMutation`: `class Input` becomes `<Name>Input` input type with `clientMutationId`. Single `input:` argument. `mutate_and_get_payload(cls, root, info, **input)`. Payload type is `<Name>Payload`. `clientMutationId` is echoed back.
- No automatic CRUD mutations. No error-as-data payloads. No transactions. No bulk mutations. All of this is left to user code or integrations.

## Interfaces and unions

- `graphene.Interface`: shared fields. `resolve_type(cls, instance, info)` classmethod. Default returns `type(instance)` for `ObjectType` instances.
- Interfaces can implement interfaces (`Meta.interfaces`, since 3.1.1).
- Interface types cannot be instantiated.
- Implementations that are not reachable from root fields must be passed in `Schema(types=[...])`.
- `graphene.Union` with `Meta.types = (A, B)`. Required and non-empty. `resolve_type` classmethod. Union options can be overridden in subclasses (3.4.2).
- Union of interfaces or of other unions is not allowed (GraphQL rule).

## Enums

- `class Episode(graphene.Enum): NEWHOPE = 4`. Backed by a Python `enum.Enum` in `Episode._meta.enum`.
- Functional form: `graphene.Enum("Episode", [("NEWHOPE", 4)])`.
- `graphene.Enum.from_enum(PyEnum, name=None, description=None, deprecation_reason=None)`. `description` and `deprecation_reason` can be callables taking the member. Type description falls back to the enum docstring, then "An enumeration." (3.3.0).
- Per-value description and deprecation from a `description` or `deprecation_reason` property on the members.
- `Episode.get(4)` for value lookup. `Episode["NEWHOPE"]` for name lookup. Enums are iterable (3.2.0) and hashable.
- Serialization accepts a member, its value, or its name (`GrapheneEnumType.serialize`).
- Resolvers get enum members as input, not raw values.
- Each `from_enum` call makes a new type. The same Python enum used twice needs the same Graphene enum object or a distinct `name`.

## Scalars

- Spec scalars: `String`, `Int` (32-bit checked), `Float`, `Boolean`, `ID`. These map to the graphql-core built-ins.
- Extra scalars: `BigInt`, `Date`, `DateTime`, `Time` (ISO 8601, `dateutil.isoparse` for `DateTime`), `Decimal` (as string), `UUID`, `JSONString` (JSON as a string), `Base64`.
- `graphene.types.generic.GenericScalar`: any JSON-like value (string, bool, int, float, list, object). Not exported at top level.
- Custom scalars: subclass `graphene.Scalar` with static `serialize`, `parse_value`, `parse_literal(node, _variables=None)`.
- No `specifiedBy` URL support for scalars. No `Upload` scalar. No `Email`, `URL`, `Duration` or similar scalars.

## Schema

- `graphene.Schema(query, mutation=None, subscription=None, types=None, directives=None, auto_camelcase=True)`.
- `auto_camelcase=True`: snake_case field and argument names become camelCase. `Field(name=...)` opts out per field.
- `directives=[GraphQLDirective, ...]`: raw graphql-core directives only. There is no Graphene class for directive definitions and no way to attach directives to types or fields.
- `str(schema)` prints SDL (`print_schema`). `schema.introspect()` returns the introspection result as a dict.
- `schema.graphql_schema`: the underlying `GraphQLSchema`. Each graphql-core type keeps its `graphene_type` (`GrapheneObjectType` and friends).
- Root types can also be raw graphql-core `GraphQLObjectType` objects.
- No SDL-first mode. No schema merging or stitching. No federation in core (`graphene-federation` is a separate package). No schema export command in core.

## Execution

- `schema.execute(query, root=, context=, variables=, operation_name=, middleware=, execution_context_class=)`. Calls `graphql_sync`. Short aliases (`root`, `context`, `variables`, `operation`) are renamed by `normalize_execute_kwargs`.
- `await schema.execute_async(...)`: calls `graphql`. Async resolvers (`async def resolve_x`) work here.
- `graphene.Context(**params)`: simple attribute bag to use as `info.context`.
- `graphene.ResolveInfo` is re-exported from graphql-core.
- Middleware: graphql-core field middleware. Object with `resolve(next, root, info, **args)` or a plain function. Runs for every field. Order is last to first in the list.
- No validation-rule argument on `execute`. To use custom rules the user calls `graphql.validate(schema.graphql_schema, parse(query), rules=...)` by hand.
- No request lifecycle hooks, no schema extensions (like Strawberry `SchemaExtension`). No tracing, no persisted queries, no caching.
- No error formatting or error masking in core. `graphene.test.Client(format_error=...)` is the only formatter hook.
- No `@defer` or `@stream`. graphql-core 3.2 does not support them.

## Subscriptions

- `Subscription` root `ObjectType`. `subscribe_<field>(root, info, **args)` as an async generator. The field resolver defaults to identity (returns the yielded value).
- `await schema.subscribe(query, ...)`: parse, validate, then returns an async iterator of `ExecutionResult`.
- No transport. No WebSocket protocol (`graphql-ws` or `graphql-transport-ws`). No SSE. No pub/sub or broadcast helpers. Those come from integrations.

## Relay

- `relay.Node` interface with an `id: ID!` field. `Meta.interfaces = (relay.Node,)` on a type. `get_node(cls, info, id)` classmethod loads the object.
- `relay.Node.Field(OnlyType=None)`: root `node(id:)` field. With a type argument it only accepts IDs of that type.
- `Node.get_node_from_global_id(info, global_id, only_type=None)` and `Node.to_global_id(type_, id)`.
- Custom nodes: subclass `Node` and override `to_global_id` and `get_node_from_global_id`. `Meta.name = "Node"` to keep the spec name.
- `Meta.global_id_type` on a custom node (3.2.0): `DefaultGlobalIDType` (base64 `Type:id`), `SimpleGlobalIDType` (raw id), `UUIDGlobalIDType` (`UUID` scalar). Custom types subclass `BaseGlobalIDType` with `graphene_type`, `resolve_global_id`, `to_global_id`.
- `relay.GlobalID(node=None, parent_type=None, required=True, global_id_type=...)`: field that encodes a local id as a global id.
- `graphene.is_node(type)` helper.
- No `nodes(ids: [ID!]!)` plural root field.
- `relay.Connection` with `Meta.node`. Auto-builds `<Name>Connection`, `<Name>Edge`, `pageInfo`, `edges`. Extra fields on the connection class and on an inner `class Edge`.
- `Meta.strict_types = True` (3.3.0): `edges: [Edge!]!` and `node: Node!`.
- `relay.ConnectionField(ShipConnection)` (alias of `IterableConnectionField`). Adds `before`, `after`, `first`, `last` arguments.
- The resolver returns an iterable or a connection instance. Slicing is done in Python by `graphql_relay.connection_from_array`. The whole list is loaded first. No `totalCount` by default. No limit on `first`/`last`. No offset pagination.
- `relay.PageInfo` with `hasNextPage`, `hasPreviousPage`, `startCursor`, `endCursor`.
- Override `resolve_connection` on a `ConnectionField` subclass for custom slicing (this is how graphene-django slices querysets).

## Dataloaders

- `graphene.utils.dataloader.DataLoader`: vendored copy of `aiodataloader` (3.1.1). Async only. `batch_load_fn(keys)` coroutine, `load`, `load_many`, `clear`, `clear_all`, `prime`. Options: `batch`, `max_batch_size`, `cache`, `get_cache_key`, `cache_map`, `loop`.
- Docs still point to the external `aiodataloader` package.
- Loaders must be created per request by the user (usually on `info.context`). No automatic loader registry. No sync dataloader.

## Validation and security

- `graphene.validation.depth_limit_validator(max_depth, ignore=[str | re.Pattern | callable], callback=fn)`: port of `graphql-depth-limit`. Introspection fields are skipped.
- `graphene.validation.DisableIntrospection`: validation rule that rejects any `__schema`/`__type` style field.
- Both must be passed to `graphql.validate` by hand. `Schema.execute` does not take rules.
- No query complexity or cost analysis. No alias limit, token limit or batch limit. No rate limiting. No per-field permissions. No authentication.

## File uploads

- Not supported in core. Docs point to `graphene-file-upload` (multipart request spec). The Relay docs show reading `info.context.FILES` by hand.

## Testing

- `graphene.test.Client(schema, format_error=None, **execute_options)`: `client.execute(query, **kwargs)` and `await client.execute_async(...)`. Returns a plain dict with `data` and `errors`.
- No pytest plugin, no fixtures, no query counting.

## Other utilities

- `graphene.utils.str_converters.to_camel_case` and `to_snake_case`.
- `graphene.utils.crunch.crunch(data)`: flatten a JSON result into a deduplicated value list. Undocumented.
- `graphene.utils.deduplicator.deflate(data)`: replace repeated `{__typename, id}` objects in a result with stubs. Undocumented.
- `graphene.utils.thenables.maybe_thenable`: run a callback on sync values or awaitables. Used for sync/async-agnostic resolvers.

## Areas not supported (core)

- ORM or data-source integration: none in core. All in separate packages.
- Filtering, ordering, query optimization, N+1 prevention: not supported. Only the manual dataloader.
- Permissions, authentication, visibility, schema hiding: not supported.
- Directives as a Python API, schema directives, federation: not supported in core.
- HTTP views, GraphiQL, WebSocket transports, persisted queries, APQ: not supported in core.
- `@defer`, `@stream`, `@oneOf`: not supported.
- Settings system: none.
- Type-hint based API and static typing support: none.

## Maintenance

- 3.3.0 (2023-07) added `strict_types` and the input `Undefined` sentinel. 3.4.x (2024-10 to 2024-11) was housekeeping: Python 3.13, removal of `aniso8601`/`pytz`, `DateTime` parsing fix, overridable Union meta, UUID parse error fix.
- No release and no commits since 2024-11-09. The README asks for contributors.

## Sources

Repo: https://github.com/graphql-python/graphene (shallow clone at `/tmp/graphene`, `master`, commit `8290326`, 2024-11-09).

Docs read (from the repo `docs/` directory, which is the source of https://docs.graphene-python.org/en/latest/):
- `docs/index.rst`, `docs/quickstart.rst`
- `docs/types/schema.rst`, `scalars.rst`, `list-and-nonnull.rst`, `objecttypes.rst`, `enums.rst`, `interfaces.rst`, `unions.rst`, `mutations.rst`
- `docs/execution/execute.rst`, `middleware.rst`, `dataloader.rst`, `fileuploading.rst`, `subscriptions.rst`, `queryvalidation.rst`
- `docs/relay/index.rst`, `nodes.rst`, `connection.rst`, `mutations.rst`
- `docs/testing/index.rst`, `docs/api/index.rst`
- `README.md`
- https://docs.graphene-python.org/llms.txt returns 404.

Changelog:
- No `CHANGELOG.md`. GitHub releases read through https://api.github.com/repos/graphql-python/graphene/releases (v3.0.0 to v3.4.3 in detail).
- https://github.com/graphql-python/graphene/releases
- PyPI release dates: https://pypi.org/pypi/graphene/json

Source files checked:
- `graphene/__init__.py`, `setup.py`
- `graphene/types/schema.py`, `field.py`, `objecttype.py`, `base.py`, `mutation.py`, `inputobjecttype.py`, `inputfield.py`, `argument.py`, `enum.py`, `interface.py`, `union.py`, `resolver.py`, `dynamic.py`, `context.py`, `utils.py`, `definitions.py`, `scalars.py`, `generic.py`, `json.py`, `datetime.py`, `unmountedtype.py`
- `graphene/relay/node.py`, `connection.py`, `mutation.py`, `id_type.py`
- `graphene/validation/depth_limit.py`, `disable_introspection.py`
- `graphene/test/__init__.py`
- `graphene/utils/dataloader.py`, `crunch.py`, `deduplicator.py`, `module_loading.py`, `resolve_only_args.py`, `subclass_with_meta.py`, `str_converters.py`
