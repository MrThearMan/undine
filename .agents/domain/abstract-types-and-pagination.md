# Abstract types and pagination

**Interface type**:
A GraphQL interface whose fields are implemented by one or more query types.
_Avoid_: InterfaceType (in prose), abstract type (GraphQL term alone)

**Interface field**:
A field declared on an interface type that implementing query types must provide.
_Avoid_: InterfaceField (in prose)

**Union type**:
A GraphQL union of multiple query types, resolved to a concrete type at runtime.
_Avoid_: UnionType (in prose)

**Relay Node**:
The Relay interface that adds an opaque global object ID to a query type.
_Avoid_: Node (unqualified), Node interface (implementation detail)

**Global object ID**:
An opaque, client-opaque identifier encoding type name and primary key, used by Relay's node refetch entrypoint.
_Avoid_: Global ID (in prose when precision matters), Relay ID

**Connection**:
A Relay pagination wrapper around a query type, union type, or interface type, exposing edges, nodes, and page info.
_Avoid_: Paginated list (when Relay cursors are meant), Connection type (GraphQL term alone)

**Page info**:
Relay metadata describing whether more pages exist before or after the current window.
_Avoid_: Pagination info, cursor info

**Offset pagination**:
Simpler pagination using offset and limit instead of Relay cursors.
_Avoid_: Limit/offset, basic pagination

**Cursor**:
The opaque identifier of a single row in a connection. It encodes the row's ordering values, so
that rows added or removed between two pages cannot move the page boundaries (keyset pagination).
For a union type or interface type connection it encodes the shared ordering values, the row's type
name, and then the ordering values of the query type the row came from.
_Avoid_: Keyset cursor (in prose), row cursor

**Ordering descriptor**:
The resolved description of one value a connection is ordered by, used to serialize that value into
a cursor and to build the row-value comparison that a cursor is applied with.
_Avoid_: Order descriptor, sort key
