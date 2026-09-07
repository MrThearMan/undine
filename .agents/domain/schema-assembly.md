# Schema assembly

## Schema

The complete GraphQL schema produced from Query, Mutation, and Subscription root types.

Avoid: API, endpoint (when meaning the whole schema)

## Root type

A Python class representing a GraphQL root object type for one operation kind. Query
(required), Mutation, or Subscription.

Avoid: RootType (in prose), operation root, top-level type

## Entrypoint

A top-level field on a root type. The place inside the schema where a query, mutation, or
subscription operation starts.

Avoid: Root field, operation field, resolver (when meaning the schema field itself)

## List entrypoint

An entrypoint on the query root type with `many=True` that returns a list of model
instances. Typically referencing a query type.

Avoid: Many entrypoint, plural entrypoint, bulk query

## Bulk mutation entrypoint

An entrypoint on the mutation root type with `many=True` that operates on a list of
inputs. Typically referencing a mutation type.

Avoid: Bulk entrypoint (ambiguous with list entrypoint), many mutation

## Connection entrypoint

An entrypoint on the query root type referencing a Connection. Typically wrapping a query
type, union type, or interface type. Returning Relay cursor-paginated results.

Avoid: Paginated entrypoint (ambiguous with offset pagination)

## Reference

The source Undine uses to derive a resolver, GraphQL type, and arguments for an
entrypoint, field, input, or filter. Common kinds include functions, Django model fields,
ORM expressions, query types, mutation types, interface types, union types, connections,
calculations, and scalars.

Avoid: Ref (in prose), backing, source type

## Converter

A single-dispatch function that derives one aspect of schema behavior (GraphQL type,
resolver, argument map, nullability, description, ...) from a reference. Extension seam:
users register new implementations rather than subclassing library types. See ADR-0001.

Avoid: Handler, resolver (that means something else), transformer

## Schema name

The name of a type or field in the generated GraphQL schema, which may differ from the
Python attribute name.

Avoid: GraphQL name, field name (ambiguous with Python)

## GraphQL Element

Any named element in the GraphQL schema: scalar, type, interface, union, enum, input or
directive.

Avoid: GraphQL type (too narrow), named type (doesn't cover directives)
