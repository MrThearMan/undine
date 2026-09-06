# graphene-sqlalchemy findings

Version checked: 3.0.0rc2 (2024-12-05, GitHub release and PyPI pre-release). The latest stable on PyPI is still 2.3.0 (2020-06-04). The 3.0 line has been beta or RC since 2021. Install needs `pip install --pre`.
Last commit on `master`: 2025-04-07. Maintenance is slow. Classifier is "Development Status :: 3 - Alpha".
Package `graphene-sqlalchemy`. Import `graphene_sqlalchemy`. Depends on `graphene>=3.0.0b7`, `SQLAlchemy>=1.1` (docs say 1.4 and 2.0 are supported), `aiodataloader`, `promise`. Python 3.9 to 3.13.
Small codebase (about 3100 lines in 9 modules). Public exports: `SQLAlchemyObjectType`, `SQLAlchemyInterface`, `SQLAlchemyConnectionField`, `get_query`, `get_session`.
It is framework-agnostic. No HTTP view, no settings module. Users serve the schema with Flask-GraphQL, Nameko or similar (see `examples/`).

## Types and fields (`graphene_sqlalchemy.types`)

- `SQLAlchemyObjectType`: `class Meta: model = UserModel`. Reflects columns, composites, hybrid properties, association proxies and relationships with `sqlalchemy.inspect(model)`.
- `SQLAlchemyInterface` (3.0.0b4): GraphQL interface from a polymorphic base model. The model must not set `polymorphic_identity` (asserted). Concrete types list it in `Meta.interfaces`.
- The `polymorphic_on` discriminator column is left out of generated fields by default. Add an `ORMField` to expose it.
- Meta options: `model`, `registry`, `skip_registry`, `only_fields`, `exclude_fields` (both at once raises `ValueError`), `interfaces`, `connection`, `connection_class`, `use_connection`, `id` (name of the id field, default `"id"`), `batching`, `connection_field_factory`, `create_filters` (default `True`), `abstract`.
- `Meta.abstract = True`: reusable base class, for example to override `get_node` for soft-delete filtering.
- `ORMField(model_attr=, type_=, required=, description=, deprecation_reason=, batching=, create_filter=, filter_type=, **field_kwargs)`: override one generated field. `model_attr` renames the field (GraphQL name differs from model attribute). Unknown `model_attr` raises `ValueError`.
- `ORMField` on composite properties cannot take any kwargs (raises `ValueError`).
- `resolve_<field>` methods override the generated resolver. Default resolver is `getattr(root, model_attr, None)`.
- Descriptions come from `Column.doc` and hybrid property docstrings (3.0.0b2).
- Nullability comes from `Column.nullable`. Primary key `Integer` columns become `ID`.
- Many-relationships are `[Child!]!` by default (3.0.0b4). Global switch `graphene_sqlalchemy.converter.set_non_null_many_relationships(False)` restores `[Child]`.
- `MyType.get_query(info)`: returns a SQLAlchemy `Query` (sync) or `select(model)` (async session) for the model. Used in custom resolvers.
- `MyType.enum_for_field("kind")`: returns the Graphene enum generated for an enum column.
- `is_type_of` raises a clear error if a coroutine is returned in sync execution ("You seem to use an async engine with synchronous schema execution").
- Reflected tables (`automap`) work. There is a test for it (`tests/test_reflected.py`), but no docs.

## Model to GraphQL type mapping (`graphene_sqlalchemy.converter.convert_sqlalchemy_type`)

- Uses a custom `singledispatchbymatchfunction` dispatcher. Extend with `@convert_sqlalchemy_type.register(column_type_eq(MyType))` or any matcher function. The same converter handles columns, hybrid property annotations and filter method annotations (3.0.0b4, PR #371).
- `String`, `Text`, `Unicode`, `UnicodeText`, PG `INET`, `CIDR`, and sqlalchemy-utils `TSVectorType`, `EmailType`, `URLType`, `IPAddressType` to `String`.
- `Integer`, `SmallInteger` to `Int` (or `ID` for primary keys). `BigInteger`, `Float`, `Numeric` to `Float`. Python `Decimal` annotation to `String`.
- `Boolean` to `Boolean`. `Date`, `Time`, `DateTime` to `Date`, `Time`, `DateTime` (these were `String` before 3.0.0b2).
- PG `UUID`, sqlalchemy-utils `UUIDType`, Python `uuid.UUID` to `UUID`.
- `JSON`, PG `JSON`, `JSONB`, `HSTORE`, sqlalchemy-utils `JSONType` to `JSONString`.
- `ARRAY` / PG `ARRAY` to nested `List` by `dimensions`. sqlalchemy-utils `ScalarListType` to `[String]`.
- `Variant` converts its `impl` type.
- `Enum` / PG `ENUM` to a Graphene `Enum`. Name comes from the Python enum class name, else the SQL enum `name`, else `<TypeName><FieldName>`. Value names are converted to UPPER_SNAKE. One Graphene enum per SQL enum is cached in the registry.
- sqlalchemy-utils `ChoiceType` to an enum named `<TABLE>_<COLUMN>`. Marked in source as inconsistent with the other enum conversion.
- `composite()` properties need an explicit converter: `@convert_sqlalchemy_composite.register(MyComposite, registry)`. Without one, schema build fails.
- `hybrid_property`: type is taken from the return type annotation (3.0.0b2). Supports scalars, `Optional[T]`, `List[T]`, other models (resolved to their registered type), forward refs and bare strings, and `Union[A, B]` / `A | B` of object types (auto-creates a `graphene.Union` named by joining the type names). Missing annotation raises `TypeError`. Known issue #396 with `from __future__ import annotations`.
- `association_proxy` (3.0.0rc1): exposed as a field of the target column type or the target relationship type. Lists are wrapped. Other targets raise `TypeError`.
- Unknown column types raise `TypeError` at schema build. The user must add a converter or set `ORMField(type_=...)`.
- No `@property` or `hybrid_method` support. Only `hybrid_property`.

## Relationships

- Many-to-one and one-to-one become a `Field(ChildType)`.
- One-to-many and many-to-many become a list field, or a connection field if the child type has a connection (child uses `relay.Node`).
- Relationship fields are `graphene.Dynamic`, so types resolve lazily from the registry. A relationship to a model with no registered type is silently dropped from the schema.
- `Meta.connection_field_factory = fn(relationship, registry, **field_kwargs)`: build custom connection fields for relationships. Default uses `UnsortedSQLAlchemyConnectionField` (deprecated class) for nested connections.
- Deprecated globals: `createConnectionField`, `registerConnectionFieldFactory`, `unregisterConnectionFieldFactory`.

## Batching / N+1 (`graphene_sqlalchemy.batching`)

- Opt-in with `Meta.batching = True` per type or `ORMField(batching=True|False)` per field (2.3.0).
- `RelationshipLoader` is a `DataLoader` that reuses SQLAlchemy internals (`strategies.SelectInLoader._load_for_path`) to load a relationship for many parents in one `SELECT ... IN`. It skips the parent query and calls the selectin loader directly. This depends on private SQLAlchemy APIs and has version branches for 1.3, 1.4 and 2.0.
- Covers all four relationship directions. One-to-many and many-to-many connections use `BatchSQLAlchemyConnectionField` (marked experimental in the source).
- Sorting works with batching (3.0.0b4, PR #355).
- Loaders are cached in a module-global dict per relationship (`RELATIONSHIP_LOADERS_CACHE`). `cache = False`, so no per-request result cache. The loader is recreated when the event loop changes (3.0.0rc1).
- Since 3.0 batching needs asyncio execution (`schema.execute_async`). Uses the DataLoader from `graphene.utils.dataloader` on graphene 3.1.1+, else `aiodataloader`.
- All parents must share one session and must not be dirty (asserted).
- No query planning or selection-set-based optimizer. No automatic `joinedload`/`selectinload` from the query. No column pruning (`load_only`). Batching is the only N+1 tool.
- Polymorphic subtypes under `SQLAlchemyInterface` are not batched. Docs tell users to set `with_polymorphic: "*"` or load explicitly. "Dynamic batching of the types based on the query ... is currently not supported."

## Relay and pagination (`graphene_sqlalchemy.fields`)

- `SQLAlchemyConnectionField(MyType.connection)`: Relay connection over a model. Adds `sort` and `filter` arguments automatically. Pass `sort=None` or `filter=None` to remove them.
- `MyType.connection` is auto-created when `interfaces = (relay.Node,)` (2.3.0). `Meta.connection_class` sets a custom `Connection` base.
- Pagination uses graphql-relay `connection_from_array_slice`. Sync: runs `query.count()`, then slices the `Query` (LIMIT/OFFSET). Async: loads all rows with `session.scalars(query).all()`, then slices in memory. Cursors are offset-based.
- `SQLAlchemyConnectionField.get_query(model, info, sort, filter, **args)`: classmethod hook to customize the base query.
- Non-null connection fields: `SQLAlchemyConnectionField(graphene.NonNull(MyType.connection))` (2.3.0).
- Node lookup: `get_node(info, id)` uses `query.get(id)` or `await session.get(model, id)` for async. Override on the type to add conditions.
- Composite primary keys: `resolve_id` returns `str(tuple(keys))` (3.0.0rc1). No matching decode in `get_node`, so node fetch with composite keys is likely not supported.
- No max page size or default page size setting. No keyset pagination. No non-Relay offset/limit list field.

## Ordering (`graphene_sqlalchemy.enums`)

- Auto sort enum per type: `<TypeName>SortEnum` with values `NAME_ASC`, `NAME_DESC` per column. Argument is `sort: [PetSortEnum]`. Default sorts by primary key(s). Docs still show old lowercase `name_asc` values.
- `MyType.sort_enum(name=, only_fields=, only_indexed=, get_symbol_name=)` and `MyType.sort_argument(enum_name=, only_fields=, only_indexed=, get_symbol_name=, has_default=)` customize the enum. `only_indexed=True` limits sorting to indexed or primary key columns.
- Only plain columns are sortable. No sorting on relationships, hybrid properties or expressions. No nulls first/last. No custom sort functions.
- Deprecated: `sort_enum_for_model`, `sort_argument_for_model`, `UnsortedSQLAlchemyConnectionField`.

## Filtering (`graphene_sqlalchemy.filters`, 3.0.0rc1, "early access")

- Built in. Replaces the third-party `graphene-sqlalchemy-filter` plugin. Auto-generated per type as `<TypeName>Filter` (`BaseTypeFilter`). Registered in the registry. Disable per type with `Meta.create_filters = False` or per field with `ORMField(create_filter=False)`.
- Only applied on `SQLAlchemyConnectionField` (`filter` argument). Plain list fields have no filter argument.
- Nested per-field syntax: `filter: {name: {eq: "Fido"}}`. Not flat `nameIn` style.
- Scalar operators (`FieldFilter`): `eq`, `nEq`, `in`, `notIn`. `StringFilter` adds `like`, `ilike`, `notlike`. `IntFilter`, `FloatFilter`, `DateFilter`, `DateTimeFilter` add `gt`, `gte`, `lt`, `lte`. `BooleanFilter`, `IdFilter`. Other scalars get a generated `Default<Scalar>ScalarFilter` with the base four.
- Enum filters: `SQLEnumFilter` and `PyEnumFilter` (only `eq`, `nEq` overridden). Generated as `Default<Enum>EnumFilter`.
- No `isNull` operator. No `not` operator. No `between`, `startsWith`, `contains` on strings, JSON or array operators. No full-text search.
- Logic: `and: [...]`, `or: [...]` lists at each filter level. Clauses go to `sqlalchemy.and_` / `or_`.
- To-one relationships: nest the related filter directly (`person: {name: {eq: "Ada"}}`). Uses an aliased JOIN.
- To-many relationships: `RelationshipFilter` (`<TypeName>RelationshipFilter`) with `contains: [...]`. Uses JOIN plus `DISTINCT`.
- `containsExactly` is in the docs and schema, but `contains_exactly_filter` raises `NotImplementedError`. Tests are `xfail`.
- Filtering over `hybrid_property` works (uses the hybrid SQL expression).
- Association proxies are not filterable.
- Custom operators: subclass a filter and add a classmethod named `<op>_filter(cls, query, field, val: T)`. The GraphQL input field is generated from the method name and the `val` type annotation. The method returns a SQL clause, or `(query, clause)` to also change the query (for example to add a join). Logic ops use the `<op>_logic` naming the same way.
- Assign a custom filter per field with `ORMField(filter_type=MyFilter)`. Register globally with `registry.register_filter_for_scalar_type(graphene.Float, MyFilter)` or `register_filter_for_enum_type`.
- No filter on arbitrary expressions or aggregates. No per-request filter restriction or permission check.

## Registry (`graphene_sqlalchemy.registry`)

- `Registry` maps models to types, and stores ORM fields, composite converters, enums, sort enums, unions, scalar filters, base type filters and relationship filters.
- `get_global_registry()`, `reset_global_registry()`. Pass `Meta.registry = Registry()` for separate schemas.
- One model maps to one type per registry. A second type for the same model silently replaces the first (the assert is commented out). Use `skip_registry=True` to avoid this.

## Sessions and async

- Session comes from `info.context["session"]` or from `Base.query = db_session.query_property()`. Missing both raises an error at query time.
- `AsyncSession` support (3.0.0b4, PR #350). Connection fields, `get_node` and batching use async calls. Needs `execute_async`.
- No session lifecycle management, no transaction handling, no per-request session creation. The user must do it.

## Mutations

- Not supported. No generated create/update/delete mutations, no input types from models, no nested writes. Users write plain `graphene.Mutation` classes.

## Permissions, validation, errors

- Not supported. No permission hooks, no query-level row filtering hook (only override `get_query` or `get_node`), no validation, no error formatting. All come from graphene or the user.

## Other areas not supported or not in scope

- No HTTP view, GraphiQL, file uploads, subscriptions, persisted queries, query complexity or depth limits, schema export command. These come from graphene or the web framework.
- No aggregation fields (count, sum) outside the Relay connection. The connection object has `.length` set but it is not exposed as a field by default.
- No settings system. Only the one global function `set_non_null_many_relationships`.
- No generic relations or polymorphic unions from models. Unions only come from `hybrid_property` `Union[...]` annotations.
- No schema hiding or field visibility per user.

## Sources

Repo: https://github.com/graphql-python/graphene-sqlalchemy (shallow clone at `/tmp/graphene-sqlalchemy`, `master`, last commit 2025-04-07).

Docs read (repo `docs/` source of https://docs.graphene-python.org/projects/sqlalchemy/en/latest/):
- `docs/index.rst`, `starter.rst`, `tutorial.rst`, `api.rst`, `examples.rst`
- `docs/inheritance.rst` (https://docs.graphene-python.org/projects/sqlalchemy/en/latest/inheritance/)
- `docs/relay.rst` (https://docs.graphene-python.org/projects/sqlalchemy/en/latest/relay/)
- `docs/tips.rst` (https://docs.graphene-python.org/projects/sqlalchemy/en/latest/tips/)
- `docs/filters.rst` (also at https://graphql-python.github.io/graphene-sqlalchemy/filters.html)
- `README.md`

Changelog: no `CHANGELOG.md` in the repo. Read all GitHub releases v1.1.0 to v3.0.0rc2 (https://github.com/graphql-python/graphene-sqlalchemy/releases). v3 tracking issue: https://github.com/graphql-python/graphene-sqlalchemy/issues/348.

Source files checked:
- `graphene_sqlalchemy/__init__.py`, `types.py`, `converter.py`, `fields.py`, `filters.py`, `batching.py`, `enums.py`, `registry.py`, `resolvers.py`, `utils.py`
- `graphene_sqlalchemy/tests/test_filters.py`, `test_batching.py`, `test_reflected.py` (grep only)
- `setup.py`, `examples/`

`/llms.txt` returned 404 on the docs site. The docs site returned 200 but was not needed because the docs source is in the repo.
