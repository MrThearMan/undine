# Relationships

How the concepts fit together across the schema.

- A **schema** is built from one **Query** root type (required) and optional **Mutation** and **Subscription** root types
- Each **root type** exposes one or more **entrypoints**
- Each **entrypoint** requires a **reference** — a query type, mutation type, interface type, union type, connection, node, function, or subscription class
- On a query root type, `many=True` with a **query type** reference creates a **list entrypoint**; with a **mutation type** reference on a mutation root type, it creates a **bulk mutation entrypoint**
- **Connection** and **offset pagination** references define their own entrypoint shapes regardless of the `many` parameter
- Interface type and union type references always resolve as lists
- A **query type** belongs to exactly one Django model and registers in the **query type registry**
- A **mutation type** belongs to exactly one Django model; its **output type** defaults to the registered **query type** for that model but can be overridden
- A **query type** may have at most one **filter set** and one **order set**, attached as class decorators or bases
- **Fields** on a **query type** that reference related models resolve through registered **query types** for those models
- **Related mutations** nest **mutation types** for related models inside a parent **mutation type**
- A **connection** wraps a **query type** (or union/interface) for Relay cursor pagination
- **Node** on a **query type** plus a `node` **entrypoint** enables **global object ID** refetch
- The **query optimizer** runs for entrypoints and fields that return querysets, building **optimization data** before queryset execution
- An **operation** passes through **lifecycle hooks** at parse, validate, execute, and per-field resolve phases

## Example dialogue

> **Dev:** "I added a `tasks` **entrypoint** with a **connection** around `TaskType`. Do clients filter through the **filter set** on the **query type**?"

> **Domain expert:** "Yes. The **filter set** on `TaskType` becomes the `filter` argument on the **connection** **entrypoint**. Client-supplied filters combine with any **queryset filter** on the **query type**."

> **Dev:** "And when they call `createTask`, the **mutation type** output is the same **query type**?"

> **Domain expert:** "Right. The **mutation type** resolves to an **output type** — usually the registered **query type**, but overridable. **Mutation type permission checks** and **mutation type validation checks** run before the write; **input-only inputs** are stripped after validation."

> **Dev:** "What does the **query optimizer** do for nested **fields**?"

> **Domain expert:** "It walks the operation's selection set and fills **optimization data** — `select_related`, `prefetch_related`, annotations — so resolving related **fields** doesn't cause N+1 queries."
