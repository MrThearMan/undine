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

To add offset pagination to a `QueryType` `Entrypoint`, you need to wrap with the `OffsetPagination`
class.

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
This makes cursor based pagination more resilient to changes in the paginated list,
since the cursors themselves do not change when items are added or removed.

Additionally, cursor based pagination wraps the paginated items as `Edge` objects inside a `Connection` object.
These objects contain additional information about the pagination state, such as the total count of items,
cursor values, or whether a next or previous page exists. For more information on cursor pagination,
see the [GraphQL Cursor Connections Specification]{:target="_blank"}.

[GraphQL Cursor Connections Specification]: https://relay.dev/graphql/connections.htm

To add cursor pagination to a `QueryType` `Entrypoint`, you need to wrap with the `Connection`
class.

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
you can do so by providing a custom `PaginationHandler` class.

```python
-8<- "pagination/connection_pagination_handler.py"
```
