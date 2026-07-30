# Filtering and ordering

**Filter set**:
A collection of filters exposed as a GraphQL input object for narrowing a queryset.
_Avoid_: FilterSet (in prose), filter input

**Filter**:
A single filter condition on a filter set, corresponding to a Django queryset lookup.
_Avoid_: Lookup (Django term alone), predicate

**Order set**:
A collection of sort options exposed as a GraphQL enum for ordering a queryset.
_Avoid_: OrderSet (in prose), sort enum

**Order**:
A single sort option within an order set, including direction and null placement.
_Avoid_: Sort, orderBy (GraphQL argument name alone)
