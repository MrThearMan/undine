# python-graphjoiner / graphlayer findings

Two projects by Michael Williamson. GraphJoiner came first. Its README says it "has been superseded by GraphLayer, which uses the same fundamental ideas with a significantly simpler API".
Both are SQLAlchemy-oriented, framework-agnostic Python libraries. No Django support. No HTTP view (graphlayer has a Flask example only). No settings module.

- graphjoiner: PyPI stable `0.3.1` (2016-11-09). Pre-releases up to `0.4.0b35` (2017-11-13). `master` setup.py is `0.4.0b35`. Last commit on `master` 2019-01-24. Depends on `graphql-core>=2.0,<3.0` and `six`. Python 2.7 and 3.3 to 3.6. About 1650 lines. Not archived. 44 stars.
- graphlayer: PyPI `0.2.8` (2019-10-18). `master` setup.py is also `0.2.8` but pins `graphql-core==3.2.3` (extra `graphlayer[graphql]`) and `python_requires>=3.7`. README says install from git. Last commit 2023-01-14 (dependabot only). Classifier "Production/Stable". About 2400 lines. Not archived. 26 stars.
- No docs site. No `docs/` directory. `graphlayer.readthedocs.io` returns 404. The READMEs are the only docs. graphlayer `README.rst` is generated from `README.src.rst` with `diff-doc` (a step-by-step tutorial).
- No changelog file in either repo. No GitHub releases. Version history only from PyPI.

## The core idea: resolve per request node, not per response node

- Normal GraphQL (graphql-core, Undine, graphene) calls a resolver for every field of every object in the response. With a SQL backend this gives N+1 queries unless you add a DataLoader or an optimizer.
- Both libraries instead walk the *query* tree once. A resolver runs once per selection in the request, not once per row. The resolver gets the whole sub-selection and returns data for all rows at once.
- Result: the number of SQL queries equals the number of relationship selections in the request. It does not depend on how many rows come back. `{ books { title author { name } } }` is always exactly 2 queries.
- The child query is built from the parent *query*, not from the parent *results*. The parent SQLAlchemy `Query` is reused as a subquery: `SELECT ... FROM author WHERE author.id IN (SELECT book.author_id FROM book WHERE book.genre = 'comedy')`. There is no need to wait for parent rows and collect IDs like a DataLoader does. Parent filters, ordering and `LIMIT` are carried into the subquery.
- Join keys are fetched as extra hidden columns on both sides. Python then groups child rows by key and attaches them to parent rows (a hash join in memory). Composite keys use `sqlalchemy.tuple_(...)`.
- Only selected columns are fetched. Each field maps to one or more SQL expressions and the SELECT list is built from the selection set. A join key column is added only if the relationship is selected.
- graphlayer README also argues a second benefit: fewer Python function calls. Call overhead scales with request size, not response size. `performance/list_of_objects.py` benchmarks this against graphql-core.
- Both libraries bypass graphql-core execution for data. They use graphql-core only to parse, validate, coerce variables, and to run introspection. Top-level `__schema` selections are split off and executed by graphql-core. The rest is run by the library's own tree walker. The results are merged.
- Difference from Undine's optimizer: Undine keeps per-field resolvers and pre-computes `select_related`/`prefetch_related`/`only` from the selection. These libraries have no per-field resolvers at all for joined data. The tree walk is the execution.
- Difference from JOIN in one statement: despite the name, graphjoiner does not emit SQL `JOIN` for relationships by default. It emits one `IN (subquery)` query per relationship. This is closer to Django `prefetch_related` with a subquery instead of an ID list.
- I think per-parent limits are not possible. `limit()` on a child query applies to the whole child query, not per parent row. There is no window-function support.

## graphjoiner core API (`graphjoiner`)

- `JoinType(name, fetch_immediates, fields, interfaces=None)`: an object type. `fields` is a callable returning a dict (lazy, for cycles).
- `fetch_immediates(selections, query, context)`: user hook. Gets the non-relationship selections (requested plus join keys) and the query for this node. Returns a list of tuples in selection order.
- `RootJoinType(name, fields)`: root with a single empty row.
- `field(type=..., **kwargs)`: scalar field. Extra kwargs (for example `column_name`) are stored on the field for `fetch_immediates` to use.
- `single(target, build_query, join=..., args=...)`, `single_or_null`, `first_or_null`, `many`: relationship fields. `build_query(args, parent_query, context)` builds the child query from the parent query. `join={"authorId": "id"}` maps parent field names to child field names. No `join` means a cross join (fine only on the root).
- `single` raises `GraphQLError("Expected 1 value but got N")` if not exactly one row. `single_or_null` raises on more than one. `first_or_null` takes the first.
- `extract(relationship, field_name)`: new field that returns one sub-field of a relationship directly (for example `bookTitles: [String]`). Main tool for many-to-many through an association type.
- `internal=True` on relationships: hidden from the schema but usable for joins and `extract`.
- `execute(root, query, variables=, context=)` and `executor(root, mutation=None)`. `executor(...)(query, schema=...)` accepts a narrower schema (see visibility below).
- Types can also be used inside a plain graphql-core schema. `Relationship.to_graphql_field` has a resolver for root-level fields (`tests/test_graphjoiner_graphql.py`).

## graphjoiner declarative API (`graphjoiner.declarative`)

- `ObjectType` subclass with class attributes as fields. `RootType` for the root. `__fetch_immediates__` and `__select_all__` class methods make a type joinable and selectable.
- `field(type=..., default=...)`, `field_set(**fields)` for dynamic field groups. Fields on superclasses and mixins are inherited.
- Snake case attribute names become camel case field names. Trailing `_` is stripped. Fields are sorted alphabetically in the schema (test `test_fields_are_in_alphabetical_ordering`).
- `__name__ = "User"` overrides the GraphQL type name.
- `single(lambda: joiner)`, `many`, `single_or_null`, `first_or_null`: relationships. The lambda defers type resolution.
- `select(target, join_query=None, join_fields=None, filter=None)`: joiner. `join_fields={Book.author_id: Author.id}` sets keys. `join_query(parent_query, child_query)` narrows the child query. `filter=fn(query)` tweaks the query (for example ordering).
- `@books.arg("genre", String)` decorator: adds an argument and a function `(query, value[, context])` that refines the query when the argument is given.
- `extract(relationship, lambda: Target.field)`: declarative form of `extract`.
- `InterfaceType` with `__interfaces__ = lambda: [HasName]` on object types. Can also implement raw graphql-core interfaces.
- `InputObjectType` with `field(type=..., default=...)`. Values are read into instances with attributes. Missing fields are `undefined` (falsy sentinel), so explicit `null` differs from absent.
- Type wrappers `Boolean`, `Float`, `Int`, `String`, `NonNull(...)`, `List(...)`. Raw graphql-core types are also accepted.
- Mutations: `Mutation` base with `__mutate__(selections, query, context)` and `mutation_field(lambda: MyMutation)`. `__args__` dict gives the arguments. Mutation root fields run serially (test `test_mutations_are_executed_serially`). No generated create/update/delete.

## graphjoiner SQLAlchemy integration (`graphjoiner.declarative.sqlalchemy`)

- `SqlAlchemyObjectType` with `__model__ = Record`. `__fetch_immediates__` runs `query.with_entities(*columns)`. Session comes from `__get_session__(context)`, default `context.session`.
- `__select_all__` adds a filter on `polymorphic_on` for single-table inheritance models (workaround for a SQLAlchemy bug).
- `column_field(Record.col, type=None, internal=False)`: type is inferred from the column. Only `Integer`, `Float`, `String`, `Boolean` are mapped. Other SQL types raise `Exception("Unknown SQL type")`. `nullable=False` gives `NonNull`.
- `sql_join(Target, join=None)`: relationship with keys found automatically from the single foreign key between the two models (either direction). Raises if the FK is missing or ambiguous. Builds `Target.__select_all__().filter(remote_col.in_(parent_query.with_entities(local_cols)))`.
- `sql_value_join(Target, join)`: executes the parent key query and passes the values to a non-SQL target. Lets a SQL type join to a static or in-memory type.
- Not supported: many-to-many helper (use `extract` with an association type), relationship introspection from `sqlalchemy.orm.relationship`, auto-generated types from models (every field is declared by hand).

## graphlayer core (`graphlayer`, imported as `g`)

- Schema types are plain objects, not classes: `g.ObjectType("Book", fields=(...), interfaces=...)`, `g.InterfaceType`, `g.InputObjectType`, `g.EnumType(PythonEnum)`, `g.ListType(T)`, `g.NullableType(T)`. Scalars `g.Boolean`, `g.Float`, `g.Int`, `g.String`.
- Everything is non-null by default. Nullability is opt-in with `NullableType`. An argument or input field with a `default` becomes nullable in the GraphQL schema.
- `g.field(name, type, params=(...))`, `g.param(name, type, default=...)`, `g.input_field(name, type, default=...)`. `fields=` can be a lambda for recursive types. Names are snake case in Python and camel case in GraphQL.
- Fields are referenced by value: `Book.fields.title`. `Root.fields.books.params.genre`. Trailing `_` works for Python keywords.
- A request becomes a typed query object tree: `ObjectQuery(type, field_queries)`, `FieldQuery(key, field, type_query, args)`, `ListQuery(element_query)`, `NullableQuery`, `ScalarQuery`, `EnumQuery`. `key` is the alias. `args` has attributes per param with defaults filled in.
- Resolvers are registered by query type: `@g.resolver(Root)`, `@g.resolver(g.ListType(Book))`, or any custom query class with a `.type` attribute. `graph.resolve(query)` dispatches on `query.type`. This lets users define their own query classes (for example `BookQuery.where(genre=...)`) and route them to resolvers.
- `g.define_graph(resolvers=...)`, `definition.create_graph({dependency_key: value})`, `g.create_graph(resolvers)`.
- Dependency injection: `@g.dependencies(session=sqlalchemy.orm.Session)` adds keyword arguments from the graph's dependency dict. Any hashable value can be a key. `Injector` itself can be injected.
- `query.create_object({key: value})` builds the result object. `g.create_object_builder(object_query)` with `.field(F)`, `.getter(F)`, `.attr(F, "name")`, `.constant(F, value)` for per-field readers. Handles `__typename` automatically for object types.
- `g.root_object_resolver(Root)` with `@resolve_root.field(Root.fields.books)` handlers `(graph, query, args)`. `g.constant_object_resolver(type, values)`.
- The graph works without GraphQL. Queries can be built in Python: `Root(Root.fields.books(Book.fields.title))`. The GraphQL layer is an optional extra. So the graph can serve as an internal data access layer.
- Query merging: `ObjectQuery.__add__` merges field queries with the same key (fragments, repeated fields). Interface queries convert to object queries with `for_type` and drop fields not on the target.
- `graphlayer.unions.select(query, select_elements, merge=)`: resolve an interface-typed query by resolving each concrete type and merging. No GraphQL union types.
- Errors: `g.GraphError`. Coercion errors for bad argument types.

## graphlayer GraphQL layer (`graphlayer.graphql`)

- `execute(document_text, graph=, query_type=, mutation_type=None, types=None, variables=None)` and `executor(query_type=, mutation_type=, types=)` (builds the graphql-core schema once).
- `parser.document_text_to_query` validates with graphql-core, then converts the AST to the query tree. Supports aliases, variables, named and inline fragments, fragments on interfaces, `@skip` and `@include`. Other directives raise "unknown directive".
- Enums map GraphQL names to Python enum *values* (`member.value`), with a TODO about names versus values.
- `__typename` is supported. `__schema` is supported only at the top level (TODO: not inside fragments).
- Mutations use the same resolver model with `mutation_type`. I think they run in field order because resolution is synchronous.
- Errors: the first error only. `ExecutionResult(data=None, errors=[error])`. No partial data, no `path`. `GraphError` becomes a plain `GraphQLError(str(error))`.
- Subscriptions: not supported ("unsupported operation").
- Async: not supported. Everything is synchronous.

## graphlayer SQLAlchemy integration (`graphlayer.sqlalchemy`, imported as `gsql`)

- `gsql.sql_table_resolver(Type, Model, fields={Type.fields.x: ...})`: resolver for one GraphQL type backed by one table. `fields` can be a lambda.
- Field kinds: `gsql.expression(Model.col)` (any SQL expression, `.map_value(fn)` to post-process), `gsql.composite((expr1, expr2), fn)` (several columns into one value), `gsql.constant(value)`, or a callable `(graph, field_query) -> field` for argument-dependent expressions.
- `gsql.join(key=Model.fk, resolve=lambda key_query: graph.resolve(...), association=None)`: relationship field. `resolve` gets the parent query with only the key columns, for use in `IN`. Multi-column keys via a tuple of columns.
- `gsql.association(table, left_key=, right_key=, distinct=False, filtered_by_left_key=False, order_by=None)`: many-to-many through an association table or a custom association `Query`.
- Result shape comes from the GraphQL type: object means exactly one (error otherwise), `NullableType` means zero or one, `ListType` means many.
- `gsql.select(type_query)` returns a SQL query object with `.where(expr)`, `.order_by(...)`, `.limit(n)`, `.group_by(...)`, `.index_by(key)`, `.by(key, values)` (index and `IN` filter). Each call returns a new object.
- The child resolver is built lazily on the first parent row. If the parent has no rows, the child query is not run.
- If no columns are selected, it selects `literal(None)` so row count still works.
- Session comes from the `sqlalchemy.orm.Session` dependency. No transaction handling.
- `gsql.forward_connection(connection_type_name=, node_type=, key=, select_by_key=)` and `graphlayer.connections.forward_connection(..., select_by_cursor=, fetch_cursors=, cursor_encoding=)`: Relay-style forward-only connection. Fields `edges { cursor node }`, `nodes`, `pageInfo { endCursor hasNextPage }`. Args `first` (required) and `after`. Keyset pagination on one ordered key with base64 int cursors (`int_cursor_encoding`). No `last`/`before`, no `totalCount`, no `hasPreviousPage`.
- No model introspection. No auto types from models. Every field and join is declared by hand.

## Visibility and schema restriction

- graphjoiner: `execute(query, schema=whitelist_schema)` runs a request against a *narrower* schema (for example built with `graphjoiner.schemas.parse_schema(sdl)`). Validation and introspection use that schema. `is_subtype` checks it is a valid sub-schema and raises `ValueError` otherwise. Usable for per-client or per-user schema hiding. Tests `test_query_can_be_executed_with_subschema`, `test_variables_are_validated_against_whitelist`.
- graphlayer: not supported.

## Not supported in either

- Custom scalars. graphjoiner accepts raw graphql-core scalars, but its SQL type mapping covers only four types. graphlayer has a `ScalarType` class, but the GraphQL schema builder only maps the four built-ins and raises "unsupported type" for others. No `ID` type in graphlayer.
- Descriptions and deprecation on types, fields or arguments.
- GraphQL union types. Custom directives. `@defer`/`@stream`.
- Filtering or ordering DSL. Only hand-written argument functions.
- Permissions, authentication, validation hooks, input-based mutations, file uploads.
- Query depth or complexity limits, persisted queries, caching, tracing, extensions or middleware.
- Subscriptions, async resolvers, HTTP views, GraphiQL (graphlayer has a Flask plus GraphiQL example in `examples/sqlalchemy/`).
- Schema export to SDL.
- Django ORM.

## Sources

Repos (shallow clones):
- https://github.com/mwilliamson/python-graphjoiner at `/tmp/python-graphjoiner` (`master`, commit `d35d31a`, 2019-01-24)
- https://github.com/mwilliamson/python-graphlayer at `/tmp/python-graphlayer` (`master`, commit `7fe773f`, 2023-01-14)

Docs read:
- graphjoiner `README.rst` (declarative and core API)
- graphlayer `README.src.rst` (tutorial source) and `README.rst`
- https://graphlayer.readthedocs.io/en/latest/ returned 404. No other docs site found.

Changelog: none in either repo. No GitHub releases. Version dates from https://pypi.org/pypi/graphlayer/json and https://pypi.org/pypi/graphjoiner/json. Repo status from https://api.github.com/repos/mwilliamson/python-graphlayer and https://api.github.com/repos/mwilliamson/python-graphjoiner.

Source files checked:
- graphjoiner: `graphjoiner/__init__.py`, `graphjoiner/requests.py`, `graphjoiner/schemas.py`, `graphjoiner/declarative/__init__.py`, `graphjoiner/declarative/sqlalchemy.py`, `setup.py`, `tests/declarative/test_declarative.py`, `tests/declarative/test_declarative_mutations.py`, `tests/test_graphjoiner_graphql.py`, `tests/test_schemas.py` (test names)
- graphlayer: `graphlayer/__init__.py`, `core.py`, `schema.py`, `resolvers.py`, `sqlalchemy.py`, `connections.py`, `unions.py`, `graphql/__init__.py`, `graphql/parser.py`, `graphql/schema.py`, `setup.py`, `examples/sqlalchemy/booksapp/`, `performance/list_of_objects.py`, all `tests/` (test names)
