description: Documentation on query pagination in Undine.

# Pagination

In this section, we'll cover the everything necessary for adding pagination
to your GraphQL schema. Undine supports both [offset](#offset-pagination)
and [cursor](#cursor-pagination) based pagination.

## Offset pagination

Offset pagination is the simplest pagination method. It allows paginating a list by specifying
an offset from the first item, and a limit for the number of items to return.

Offset pagination works well for lists where each item's index never changes,
e.g., a list sorted by a timestamp or an auto-incrementing primary key.
If this is not the case, you should use [cursor](#cursor-pagination) based pagination instead,
because changes in the middle of the list between page queries can cause items to be skipped or duplicated.

To add offset pagination to an `Entrypoint`, you need to wrap the `QueryType`, `UnionType`, or
`InterfaceType` with the `OffsetPagination` class.

```python hl_lines="11"
-8<- "pagination/offset_entrypoint.py"
```

This creates the following GraphQL types.

```graphql hl_lines="10 11"
type TaskType {
  pk: Int!
  name: String!
  done: Boolean!
  createdAt: DateTime!
}

type Query {
  pagedTasks(
    offset: Int
    limit: Int
  ): [TaskType!]!
}
```

Offset pagination can also be used with many-related `Fields`.

```python hl_lines="11"
-8<- "pagination/offset_field.py"
```

This creates the following GraphQL types.

```graphql hl_lines="14 15"
type PersonType {
  pk: Int!
  name: String!
  email: Email!
  tasks: [TaskType!]!
}

type TaskType {
  pk: Int!
  name: String!
  done: Boolean!
  createdAt: DateTime!
  assignees(
    offset: Int
    limit: Int
  ): [PersonType!]!
}

type Query {
  pagedTasks(
    offset: Int
    limit: Int
  ): [TaskType!]!
}
```

## Cursor pagination

Cursor based pagination works by assigning items an opaque unique identifier called a "cursor".
Pages can then be defined as starting before or after a given cursor.

A cursor identifies a *row* rather than a position in the list: it encodes the values the list is
ordered by for the item it points to. Paginating "after" a cursor therefore means "give me the items
that sort after this item", which makes cursor pagination resilient to items being added to or removed
from the parts of the list that have already been read. Items are never skipped or delivered twice
because of a change earlier in the list, which is what makes it a good fit for infinite scrolling
and for lists that change while they are being read.

Two things follow from cursors being tied to the ordering:

- A cursor is only valid for the ordering it was issued under. Replaying a cursor after changing the
  [`OrderSet`](ordering.md#orderset) arguments may return a `Bad Request` error, since no pagination
  scheme can say what comes "after" an item under an ordering that item was never sorted by.
- The primary key is always appended to the ordering, so that no two items compare equal.
  If no ordering is requested, items are ordered by their primary key.

Additionally, cursor based pagination wraps the paginated items as `Edge` objects inside a `Connection` object.
These objects contain additional information about the pagination state, such as the total count of items,
cursor values, or whether a next or previous page exists. For more information on cursor pagination,
see the [GraphQL Cursor Connections Specification]{:target="_blank"}.

[GraphQL Cursor Connections Specification]: https://relay.dev/graphql/connections.htm

To add cursor pagination to a `QueryType`, `UnionType` or `InterfaceType`, `Entrypoint`,
you need to wrap with the `Connection` class.

```python hl_lines="11"
-8<- "pagination/connection_entrypoint.py"
```

This creates the following GraphQL types.

```graphql
type TaskType {
  pk: Int!
  name: String!
  done: Boolean!
  createdAt: DateTime!
}

type TaskTypeEdge {
  cursor: String!
  node: TaskType
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

type TaskTypeConnection {
  totalCount: Int!
  pageInfo: PageInfo!
  edges: [TaskTypeEdge!]!
}

type Query {
  pagedTasks(
    after: String
    before: String
    first: Int
    last: Int
  ): TaskTypeConnection!
}
```

Querying this `Entrypoint` will return a response like this:

```json
-8<- "pagination/response_1.json"
```

Similarly, cursor pagination can also be used with many-related `Fields`.

```python hl_lines="11"
-8<- "pagination/connection_field.py"
```

Note that for nested `Connections`, a single `after` or `before` cursor is shared by every parent item.
Since a cursor points to a row and not to an index, each parent's list begins at the first item that
sorts after that cursor, which can be a different position in each parent's list.

> For Relay-compliant clients, see the [Global Object IDs](global-object-ids.md#node-interface) section
> for adding support for the `Node` interface.

## Filtering and ordering

If a [`FilterSet`](filtering.md#filterset) or an [`OrderSet`](ordering.md#orderset)
has been added to a `QueryType`, their arguments will be added to the `Entrypoint`
along with the pagination arguments for the specific pagination method. For example,
for a `Connection` `Entrypoint`:

```graphql
type Query {
  pagedTasks(
    after: String
    before: String
    first: Int
    last: Int
    filter: TaskFilterSet
    orderBy: [TaskOrderSet!]
  ): TaskTypeConnection!
}
```

## Page size

The default page size for all pagination methods is set by the
[`PAGINATION_PAGE_SIZE`](settings.md#pagination_page_size) setting.
You can also use a different page size by using the `page_size` argument.

```python
-8<- "pagination/connection_page_size.py"
```

Setting page size to `None` will return all items in a single page.

## Custom pagination strategies

The default pagination strategies are accurate and performant for both top-level and nested fields
(although calculating `totalCount` for nested `Connections` can be slow,
since it requires a subquery for each parent item).
Still, if you need to modify the pagination behavior,
you can do so by providing a custom pagination handler class.

All `Connections` use the `CursorPaginationHandler`, which implements the cursor pagination
described above. For a `UnionType` or an `InterfaceType`, a cursor encodes the ordering values
the members share, the type name of the row, and then the ordering values of the query type the
row came from. `OffsetPagination` uses the `OffsetPaginationHandler` instead, which pages with
`offset` and `limit`.

```python
-8<- "pagination/connection_pagination_handler.py"
```
