# Read model

**Query type**:
A GraphQL object type backed by a Django model, defining how that model is read through the API.
_Avoid_: QueryType (in prose), output type (without qualifier), ObjectType (GraphQL term alone)

**Field**:
A queryable attribute declared on a query type, exposed as a GraphQL field on that type. In Undine discussions, "field" alone means this — not a Django model field or a generic GraphQL field elsewhere in the schema.
_Avoid_: Attribute, column, model field, GraphQL field (without qualifier)

**Query type registry**:
The mapping from each Django model to its registered query type, used to wire relations and mutation outputs.
_Avoid_: Registry (unqualified), type map

**Calculation**:
A computed value on a query type defined by a database expression with optional arguments, rather than a plain model attribute.
_Avoid_: Computed field, annotation (Django term alone)

**Autogeneration**:
Introspection of a Django model to produce fields, inputs, filters, or orders without hand-declaring each one.
_Avoid_: Auto, codegen, schema generation
