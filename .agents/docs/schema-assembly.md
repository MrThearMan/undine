# Schema assembly

**Schema**:
The complete GraphQL schema produced from Query, Mutation, and Subscription root types.
_Avoid_: API, endpoint (when meaning the whole schema)

**Root type**:
A Python class representing a GraphQL root object type for one operation kind — Query (required), Mutation, or Subscription.
_Avoid_: RootType (in prose), operation root, top-level type

**Entrypoint**:
A top-level field on a root type — the place inside the schema where a query, mutation, or subscription operation starts.
_Avoid_: Root field, operation field, resolver (when meaning the schema field itself)

**List entrypoint**:
An entrypoint on the query root type with `many=True` that returns a list of model instances — typically referencing a query type.
_Avoid_: Many entrypoint, plural entrypoint, bulk query

**Bulk mutation entrypoint**:
An entrypoint on the mutation root type with `many=True` that operates on a list of inputs — typically referencing a mutation type.
_Avoid_: Bulk entrypoint (ambiguous with list entrypoint), many mutation

**Connection entrypoint**:
An entrypoint on the query root type referencing a Connection — typically wrapping a query type, union type, or interface type — returning Relay cursor-paginated results.
_Avoid_: Paginated entrypoint (ambiguous with offset pagination)

**Reference**:
The source Undine uses to derive a resolver, GraphQL type, and arguments for an entrypoint, field, input, or filter. Common kinds include functions, Django model fields, ORM expressions, query types, mutation types, interface types, union types, connections, calculations, and scalars.
_Avoid_: Ref (in prose), backing, source type

**Schema name**:
The name of a type or field in the generated GraphQL schema, which may differ from the Python attribute name.
_Avoid_: GraphQL name, field name (ambiguous with Python)

**GraphQL Element**:
Any named element in the GraphQL schema: scalar, type, interface, union, enum, input or directive.
_Avoid_: GraphQL type (too narrow), named type (doesn't cover directives)
