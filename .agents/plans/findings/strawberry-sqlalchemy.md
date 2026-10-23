# strawberry-sqlalchemy findings

Version checked: 0.9.0 (2026-08-31, PyPI and `CHANGELOG.md`). Last commit on `main`: 2026-09-17. PyPI classifier is "Development Status :: 5 - Production/Stable". Version is still 0.x.
Package `strawberry-sqlalchemy-mapper`. Import `strawberry_sqlalchemy_mapper`. Depends on `strawberry-graphql>=0.288.0`, `SQLAlchemy>=1.4` (with `asyncio` extra), `sqlakeyset`, `sentinel`, `typing-extensions`. Python 3.10 to 3.14.
Small codebase (about 2600 lines in 7 modules). Public exports: `StrawberrySQLAlchemyMapper`, `StrawberrySQLAlchemyLoader`, `field`, `connection`, `node`, `BigInt`, `strawberry_sqlalchemy_scalar_map`.
No real docs. The `docs/` directory is an unedited Sphinx template. The README is the only user documentation. strawberry.rocks has no page for it.
It is framework-agnostic. No HTTP view, no settings module. It only builds Strawberry types and resolvers.

## Types and fields (`StrawberrySQLAlchemyMapper`)

- `mapper = StrawberrySQLAlchemyMapper(model_to_type_name=, model_to_interface_name=, extra_sqlalchemy_type_to_strawberry_type_map=, always_use_list=False)`. One mapper instance holds all generated types.
- `@mapper.type(Model, make_interface=False, use_federation=False, directives=())`: decorate an empty class. Adds fields for all columns, relationships, association proxies and hybrid properties. Then calls `strawberry.type`, `strawberry.interface` or `strawberry.federation.type`.
- `__exclude__ = ["password_hash"]` on the class: skip fields. There is no `__include__` / only-fields option.
- `__use_list__ = ["employees"]` on the class: make these to-many relationships plain lists instead of connections (0.5.0).
- Fields declared by hand on the class override generated ones. Private annotations (`strawberry.Private`) are kept.
- `mapper.finalize()`: must be called before `strawberry.Schema(...)`. Auto-maps every model reached through relationships (transitively) with an empty type. Fixes forward-ref namespaces so relationship types resolve across modules.
- `mapper.mapped_types`, `mapped_interfaces`, `edge_types`, `connection_types`: dicts of generated types. README says pass `list(mapper.mapped_types.values())` to `Schema(types=...)` for polymorphic types.
- Type naming: `model_to_type_name` (default `Model.__name__`) and `model_to_interface_name` (default `<Model>Interface`). Names must be consistent because relationships use them as forward refs.
- Type inheritance (0.6.4): a mapped type can subclass another mapped type. Inherits fields and `__exclude__`. Own model fields win over inherited ones. Explicit class fields win over both.
- `directives=[...]` on `mapper.type` (0.6.0). `use_federation=True` uses `strawberry.federation.type`. No other federation helpers.
- Auto `is_type_of`: `type(obj) is model`. Used for interfaces and unions.
- No field descriptions from `Column.doc`, comments or docstrings. No type description from the model docstring.
- No per-field rename of generated fields. Only a hand-written field can set a different name.
- `strawberry_sqlalchemy_mapper.field(...)`: a `strawberry.field` clone that also takes `sessionmaker=`. Used internally for all generated fields.

## Model to GraphQL type mapping

- Lookup is `isinstance` over an ordered dict `sqlalchemy_type_to_strawberry_type_map`. Extend with `extra_sqlalchemy_type_to_strawberry_type_map={MyType: str}`. README says `TypeDecorator` support is untested.
- `Integer`, `SmallInteger` to `int`. `Float` to `float`. `Numeric` to `Decimal`. `String`, `Text`, `Unicode`, `UnicodeText`, `VARCHAR` to `str`. `Boolean` to `bool`. `DateTime`, `Date`, `Time` to `datetime`, `date`, `time`. PG `UUID` to `uuid.UUID`. `JSON` to `strawberry.scalars.JSON` (0.2.0).
- `BigInteger` to custom `BigInt` scalar (0.4.2). Since 0.9.0 the user must register `StrawberryConfig(scalar_map=strawberry_sqlalchemy_scalar_map)` or schema build fails. Its `parse_value` returns `str(v)`, so input values come in as strings.
- `ARRAY(T)` to `List[T]` (item type mapped recursively).
- `Enum` columns use the Python enum class (`column.type.python_type`). The user must decorate that enum with `@strawberry.enum`. No auto-generated GraphQL enum. I think string-only `Enum("a", "b")` columns become `str` (SQLAlchemy `python_type` falls back to `str`).
- `LargeBinary` is silently skipped (`SkipTypeSentinel`).
- Unknown column types raise `UnsupportedColumnType` at decoration time. Fix is `__exclude__` or a map entry.
- Nullability comes from `Column.nullable`. Primary keys are not turned into `ID`.
- `hybrid_property`: type comes from the return annotation. Missing annotation raises `HybridPropertyNotAnnotated`. String annotations are parsed with `ast.literal_eval`, so most forward refs fail with `UnsupportedDescriptorType`. The hybrid is only readable. No SQL expression use.
- Other ORM descriptors (`column_property` is a column so it works, but plain `@property`, `hybrid_method`, `composite`, `synonym`) raise `UnsupportedDescriptorType` or are ignored. No composite support.

## Relationships

- Many-to-one becomes `Type` or `Optional[Type]` (optional if any local FK column is nullable). One-to-many and many-to-many become a generated `<Type>Connection` by default, or `List[Type]` with `__use_list__` or `always_use_list=True` (0.8.0).
- Generated connection types: `<Type>Connection` (subclass of `strawberry.relay.ListConnection`) and `<Type>Edge`. Connection fields take `first`, `after`, `last`, `before` (cursor pagination on relationships added in 0.7.0). Cursors are offset-based (`arrayconnection:<index>`).
- `relationship.order_by` is applied. No other ordering on relationship fields.
- `association_proxy("rel1", "rel2")` (relationship through relationship) is supported and batched through both loaders. Other shapes raise `UnsupportedAssociationProxyTarget`. Association proxy connections take no pagination arguments.
- If the relationship is already loaded on the instance (for example with `selectinload`), the resolver uses it and skips the loader.

## Batching / N+1 (`StrawberrySQLAlchemyLoader`)

- The user must put `StrawberrySQLAlchemyLoader(bind=session)` or `StrawberrySQLAlchemyLoader(async_bind_factory=async_sessionmaker)` in context under `sqlalchemy_loader` (dict key or attribute). Create one per request. Async support added in 0.3.0.
- One Strawberry `DataLoader` per relationship, per pagination-argument combination (`PaginatedLoader`, 0.7.0). Query is `SELECT related WHERE (remote cols) IN (keys)`. Works with composite keys via `tuple_`. Many-to-many with `secondary` is tested.
- All relationship resolvers are `async`. Sync execution (`execute_sync`) does not work for relationship fields. Tests call `schema.execute` with `asyncio.run` and carry a "TODO: get execute_sync to work" note.
- With `async_bind_factory`, each batch opens a new session. Loaded objects come from a different session than the parent.
- I think pagination on batched relationships is wrong for more than one parent. `OFFSET` and `LIMIT` are applied to the whole `IN (...)` query, not per parent. `last` also counts rows over all keys. Tests only use a single parent (`tests/test_relationship_pagination.py`).
- No query planning or selection-set optimizer. No automatic `joinedload`/`selectinload`. No column pruning (`load_only`). All columns of the related model are always selected.
- No batching for root fields. The user writes root resolvers with plain `session.scalars(select(...))`.

## Relay (`strawberry_sqlalchemy_mapper.relay`, 0.4.0)

- Subclass `relay.Node` on a mapped type. The mapper injects `resolve_id`, `resolve_id_attr`, `resolve_node`, `resolve_nodes` unless the user overrides them.
- ID attribute is `relay.NodeID` annotation if present, else the primary key column names. Composite primary keys are joined with `|` and split back on lookup. Each part is converted with the column `python_type`.
- `node(sessionmaker=...)`: root node field. Works for `Type`, `Optional[Type]` and `List[Type]` (many ids). Async sessions run through `session.run_sync`.
- `connection(ConnType, sessionmaker=..., keyset=(Model.col,), resolver=...)`: root connection field. Without a resolver it queries the whole model with legacy `session.query(model)`. With a resolver, the resolver returns a `Query` to paginate.
- `relay.ListConnection[T]`: offset pagination through Strawberry. `KeysetConnection[T]`: keyset (seek) pagination through `sqlakeyset.get_page`, with cursors from `sqlakeyset` bookmarks. `keyset=` sets the `ORDER BY`. Async keyset pagination uses `run_sync` because `sqlakeyset` has no async API.
- Page size limit comes from Strawberry `StrawberryConfig(relay_max_results=...)`. Checked in `KeysetConnection`.
- Node ids are the `ID` scalar since 0.9.0 (Strawberry `relay_use_legacy_global_id` default).
- No `totalCount` field on generated connections.
- Relay requires the legacy `Query` API (`session.query`). No 2.0-style `select()` path.

## Ordering and filtering

- Not supported. `ordering.py` is an empty file. No generated order or filter inputs, no filter arguments on connections or lists. The user writes arguments and query code by hand in a `connection(resolver=...)` or a plain field.

## Polymorphism and interfaces

- `@mapper.interface(BaseModel)`: GraphQL interface for the base of a polymorphic hierarchy (`polymorphic_on` set). Other models raise `InterfaceModelNotPolymorphic`.
- Concrete types for the base and each subclass are declared with `@mapper.type(...)`. Relationships to a polymorphic base return the interface type.
- No unions generated from models.

## Mutations and input types

- Not supported. No input types from models, no create/update/delete mutations, no nested writes, no validation.

## Permissions, errors, context

- Not supported by the library. `field(permission_classes=...)` is passed through to Strawberry. No row-level filtering hook for relationships or connections. No custom error types.
- No session lifecycle management beyond `connection(sessionmaker=...)` opening a session per connection field with `with session as s`. No transaction handling.

## Other areas not supported or not in scope

- No HTTP view, GraphiQL, subscriptions, file uploads, persisted queries, complexity or depth limits, schema export. These come from Strawberry.
- No aggregation fields (count, sum). No `totalCount`.
- No settings system. Only mapper constructor arguments.
- No visibility or schema hiding per user.
- No real documentation site or API reference.

## Sources

Repo: https://github.com/strawberry-graphql/strawberry-sqlalchemy (shallow clone at `/tmp/strawberry-sqlalchemy`, `main`, last commit 2026-09-17).

Docs read:
- `README.md` (the only user docs)
- `docs/index.rst` (Sphinx template only, no content)
- https://strawberry.rocks/docs (no SQLAlchemy page. `/docs/integrations/sqlalchemy` and `/llms.txt` returned 404)
- https://strawberry-sqlalchemy-mapper.readthedocs.io/en/latest/ returned 404

Changelog: `CHANGELOG.md` (0.1.2 to 0.9.0). `CHANGELOG.rst` is a template placeholder. PyPI JSON for version and classifiers: https://pypi.org/pypi/strawberry-sqlalchemy-mapper/json

Source files checked:
- `src/strawberry_sqlalchemy_mapper/__init__.py`, `mapper.py`, `loader.py`, `field.py`, `relay.py`, `scalars.py`, `exc.py`, `utils.py`, `pagination_cursor_utils.py`, `ordering.py` (empty)
- `tests/test_relationship_pagination.py`, `tests/test_loader.py`, `tests/relay/test_connection.py`, `tests/relay/test_node.py`, `tests/test_association_proxy.py`, `tests/test_mapper_inheritance.py` (test names and fixtures)
- `pyproject.toml`
