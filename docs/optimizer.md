description: Documentation on the query optimizer in Undine.

# Optimizer

This section covers Undine's query optimizer, which is responsible for
optimizing queries to your GraphQL schema in order to reduce the amount
of database queries that are made when resolving a request.

## The Problems

Before we take a look at _how_ the optimizer works, let's first
understand _why_ it exists by going over some common problems
that arise when using GraphQL to fetch data from a relational database.

### The N+1 Problem

Let's say you have a collection of Models like this:

```python
-8<- "optimizer/models_1.py"
```

And a schema like this:

```graphql
type ProjectType {
  pk: Int!
  name: String!
}

type StepType {
  pk: Int!
  name: String!
  done: Boolean!
}

type TaskType {
  pk: Int!
  name: String!
  description: String!
  project: ProjectType!
  steps: [StepType!]!
}

type Query {
  tasks: [TaskType!]!
}
```

Now, let's say you query `tasks` like this:

```graphql
query {
  tasks {
    pk
    name
    description
    project {
      pk
      name
    }
    steps {
      pk
      name
      done
    }
  }
}
```

In GraphQL, each field in the query will be resolved separately, and most importantly,
if a field returns a list of objects with subfields, the resolvers for those
subfields will be called for each object in the list. Normally, a field's resolver
knows nothing about the query it is in, and so it only fetches the data it needs.

In this case, the top level resolver for `tasks` will fetch all `Task` objects,
but won't make any joins to related Models its subfields might need. For example,
when the subfield for the related `Project` resolves, that resolver will
try to look up the `Project` from the root `Task` instance it received, but since the
`Project` was not fetched along with the `Task`, it needs to make another query to the database.

This means that for the whole query we first fetch all `Tasks`, and then all `Projects`
and `Steps` for each `Task`. If we had 100 `Tasks`, each of which is linked to a `Project`,
but also to 10 `Steps`. In total this would result in **_201_** queries to the database!

It's important to notice that the amount of queries is proportional to the amount of `Tasks` in the database.
You can imagine how this can get out of hand quickly, especially when you start nesting
relations deeper and deeper. Each additional level of nesting will grow the number of queries
exponentially! That's why it's called the **N+1 problem**: 1 query for the root object,
and N queries for all subfields, where N is the amount of root objects.

### Over-fetching

Another issue with resolving Django Models using normal resolvers is that
when a Model is fetched from the database, all of its non-relational fields
are also fetched by default. This means that we'll fetch fields that are
not needed in the query. This can be expensive if the Model has many fields
or fields that contain a lot of data. This is called **over-fetching**,
in contrast to the N+1 problem, which is a problem of **under-fetching**.

## The Optimizer

Undine includes an optimizer that fixes the above problems automatically
by introspecting the incoming query and generating the appropriate
`QuerySet` optimizations like `prefetch_related` and `select_related` calls.
It plugs into the top-level resolvers in the schema, so in the above example,
the resolver for the `tasks` `Entrypoint`, and makes the necessary optimizations
to reduce the amount of database queries made. This way all subfields can resolve normally,
knowing that the data they need is already fetched.

For the most part, this is all you need to know about the optimizer. However,
there are a few things you need to know to not break these optimizations.

Be careful when overriding `Field` resolvers. If you define a custom resolver
for Model field which uses Model data outside of the field itself,
those fields may not have been fetched if they are not also part of the query.
More generally, you need to be careful when using Models outside of the GraphQL context.
A common place where this may happen is in permission checks, which often need to access
Model data for object permissions, etc.

To deal with this, Undine includes methods to specify additional optimizations manually,
see the [Manual Optimizations](#manual-optimizations) section below.

### Manual Optimizations

The `QueryType.__optimizations__` method is called by the optimizer when an `Entrypoint`
or `Field` using the given `QueryType` is included in the query.
See [optimization data](#optimization-data) on how to add the optimizations.

```python
-8<- "optimizer/querytype_optimizations.py"
```

The `<field_name>.optimize` method is called by the optimizer when the given `Field`
is included in the query. See [optimization data](#optimization-data) on how to add the optimizations.

```python
-8<- "optimizer/field_optimize.py"
```

### Optimization data

The `OptimizationData` object holds the optimizations that the optimizer gathers
from the query. You can add new optimizations to the data to ensure that, e.g., required fields
are fetched, even if they are otherwise not needed in the query. Let's go over the structure of
the `OptimizationData` object.

#### `model`

This is the Model class which the optimizations in the data correspond to.
Set by the optimizer and should not be modified.

#### `info`

The resolver info object for the request, as it applies for this `OptimizationData`.
During field resolving, the `field_name`, `field_nodes`, `return_type` and `parent_type`
of the resolver info object are different depending on the `ObjectType` being resolved,
so each `OptimizationData` needs to know how the resolver info would look when its
`ObjectType` is being resolved. Various methods in Undine get passed this `info` object
so that users of the library can use it do their own introspections.

#### `related_field`

The related Model field being optimized. Can be `None` if the `OptimizationData` is for the root-level.

#### `parent`

If the `OptimizationData` is for a related Model, this links to the
optimization data of the parent Model. Conversely, the `parent` `OptimizationData`
has a link this `OptimizationData` using either [`select_related`](#select_related),
[`prefetch_related`](#prefetch_related) or [`generic_prefetches`](#generic_prefetches).

#### `only_fields`

Contains fields that will be applied to `QuerySet.only()`. This prevents the
[over-fetching](#over-fetching) issue by only fetching the required fields for the query.
If the [`DISABLE_ONLY_FIELDS_OPTIMIZATION`](settings.md#disable_only_fields_optimization)
setting is `True`, these values will be ignored when the optimizations are applied.

#### `aliases`

Contains the Django ORM expressions that will be applied to `QuerySet.alias()`. Various
methods in Undine can add to these aliases to enable more clearer use of
for [`annotations`](#annotations).

#### `annotations`

Contains the Django ORM expressions that will be applied to `QuerySet.annotate()`.
`Fields` that resolve using an expression will store their expression here.

#### `select_related`

Contains `OptimizationData` for related fields that should be fetched together
using `QuerySet.select_related()`. New related fields should be added using
[`add_select_related`](#add_select_related) to ensure that the correct references
are places in both `OptimizationData`.

#### `prefetch_related`

Contains `OptimizationData` for related fields that should be fetched together
using `QuerySet.prefetch_related()`. New related fields should be added using
[`add_prefetch_related`](#add_prefetch_related) to ensure that the correct references
are places in both `OptimizationData`.

Note that the key in the mapping can be either the name of the related field,
or an alias that the data should be fetched with (using `Prefetch(..., to_attr=<alias>)`).

#### `generic_prefetches`

Contains `OptimizationData` for generic foreign keys that should be fetched together
using `QuerySet.prefetch_related()`. New generic prefetches should be added using
[`add_generic_prefetch_related`](#add_generic_prefetch_related) to ensure that the correct references
are places in both `OptimizationData`.

#### `filters`

Contains `Q` expressions that will be applied to `QuerySet.filter()`.
Normally, these are compiled from a `FilterSet`.

#### `order_by`

Contains `OrderBy` expressions that will be applied to `QuerySet.order_by()`.
Normally, these are compiled from an `OrderSet`.

#### `distinct`

Whether `QuerySet.distinct()` should be applied. Normally, the optimizer is able
to determine this based on the `FilterSet` `Filters` used in the query.

#### `none`

Whether `QuerySet.none()` should be applied. Note that using `QuerySet.none()`
will result in an empty `QuerySet` regardless of other optimizations.
Normally, this is only applied if a `FilterSet` `Filter` raises an
`EmptyFilterResult` exception.

#### `pagination`

Contains the pagination information for the `QuerySet` in the form of a
`PaginationHandler` object. Normally, this is set by the optimizer automatically
based on if the field uses a [pagination](pagination.md) or not.

#### `queryset_callback`

A callback function that initializes the `QuerySet` for the `OptimizationData`.
By default, this is set to use the `Manager.get_queryset()` method of the
`OptimizationData` [`Model`](#model) default manager, or the
`QueryType.__get_queryset__` method for related fields to other `QueryTypes`.

#### `pre_filter_callback`

A callback function that will be called before [`order_by`](#order_by), [`distinct`](#distinct),
[`filters`](#filters), or [`field_calculations`](#field_calculations) are applied to the
`QuerySet`. Normally, this is populated using the `QueryType.__filter_queryset__` method.

#### `post_filter_callback`

A callback function that will be called after [`order_by`](#order_by), [`distinct`](#distinct),
[`filters`](#filters), and [`field_calculations`](#field_calculations) are applied to the
`QuerySet`. Normally, this is populated using the  `FilterSet.__filter_queryset__` method.

#### `field_calculations`

A list of [`Calculation`](queries.md#calculation-references) _instances_ that should be run
and annotated to the `QuerySet`. Normally, the optimizer will automatically add `Fields`
using `Calculation` objects to this list.

#### `add_select_related()`

A method for adding a new `select_related` optimization. Must provide the
`field_name` for the model relation, and optionally a `QueryType` that the relation
should use.

This method will make sure that the created `select_related` optimization
has the correct references to its parent `OptimizationData`, which it needs so that
it can be compiled correctly. Passing the `QueryType` will fill the [`queryset_callback`](#queryset_callback),
[`pre_filter_callback`](#pre_filter_callback), and [`post_filter_callback`](#post_filter_callback)
from the `QueryType` as well.

#### `add_prefetch_related()`

A method for adding a new `prefetch_related` optimization. Must provide the
`field_name` for the model relation, and optionally a `QueryType` that the relation
should use, as well as a `to_attr` for the prefetch alias.

This method will make sure that the created `prefetch_related` optimization
has the correct references to its parent `OptimizationData`, which it needs so that
it can be compiled correctly. Passing the `QueryType` will fill the [`queryset_callback`](#queryset_callback),
[`pre_filter_callback`](#pre_filter_callback), and [`post_filter_callback`](#post_filter_callback)
from the `QueryType` as well.

The string passed in `to_attr` will be used in `Prefetch(..., to_attr=<to_attr>)`,
which will prefetch the related field to the given attribute name. Normally, the optimizer
uses this to fetch many-related fields fetched with aliases or defined using custom schema names.

#### `add_generic_prefetch_related()`

A method for adding a new `generic_prefetch_related` optimization. Must provide the
`field_name` for the model relation, the `related_model` that the generic prefetch
should be done for, and optionally a `QueryType` that the relation should use,
and `to_attr` for the prefetch alias.

This method will make sure that the created `generic_prefetch_related` optimization
has the correct references to its parent `OptimizationData`, which it needs so that
it can be compiled correctly. Passing the `QueryType` will fill the [`queryset_callback`](#queryset_callback),
[`pre_filter_callback`](#pre_filter_callback), and [`post_filter_callback`](#post_filter_callback)
from the `QueryType` as well.

The string passed in `to_attr` will be used in `GenericPrefetch(..., to_attr=<to_attr>)`,
which will prefetch the related field to the given attribute name. Normally, the optimizer
uses this to fetch generic relations fetched with aliases or defined using custom schema names.

### Optimization results

Once the whole query has been analyzed, the `OptimizationData` is processed to
`OptimizationResults`, which can then be applied to the `QuerySet`. This processing
simply copies over most of the data from the `OptimizationData`, but notably,
it also converts any `select_related`, `prefetch_related`, or `generic_prefetch_related`
optimizations to values that can be applied to a `QuerySet`.

For `select_related`, this means either [promotion to a prefetch](#promotion-to-prefetch),
or extending the related field's optimizations to the parent Model. For example,
querying the `name` of a `Project` related to a `Task` will extend the lookup to the `Task` Model
(i.e. `project__name`). This lookup is then added to the `Task` Model's `OptimizationResults.only_fields`.

For `prefetch_related`, the prefetch `OptimizationResults` are processed
and applied to the queryset taken from `OptimizationResults.queryset_callback`.
The resulting `Prefetch()` object is added to the parent `OptimizationResults.prefetch_related`.

`generic_prefetch_related` is processed similarly to `prefetch_related`,
expect a `GenericPrefetch()` object is created instead.

#### Promotion to prefetch

In certain cases, a `select_related` optimization must be promoted to a `prefetch_related`.
This can happen for one of the following reasons:

1. Any [`annotations`](#annotations) (or [`aliases`](#aliases)) are requested from the relation.
   A prefetch must be made so that the annotation remains available in the related object.
2. Any [`field_calculations`](#field_calculations) are present. Calculation will become annotations,
   so the reason is the same as above.
3. A `pre_filter_callback` or `post_filter_callback` is needed. Since these callbacks might filter out
   the related object, a prefetch must be done to ensure this. Note that this might result in
   a null value for a field that would otherwise not be null!

### Order of optimizations

`OptimizationResults` properties are applied to a `QuerySet` in the following order:

1. If `none` is `True`, return an empty `QuerySet` and exit early.
2. If `select_related` is not empty, apply them using `QuerySet.select_related()`.
3. If `prefetch_related` is not empty, apply them using `QuerySet.prefetch_related()`.
4. If  the [`DISABLE_ONLY_FIELDS_OPTIMIZATION`](settings.md#disable_only_fields_optimization)
   setting is `False`, and `only_fields` is not empty, apply them using `QuerySet.only()`.
5. If `aliases` is not empty, apply them using `QuerySet.alias()`.
6. If `annotations` is not empty, apply them using `QuerySet.annotate()`.
7. If `pre_filter_callback` exists, call it.
8. If `order_by` is not empty, apply them using `QuerySet.order_by()`.
9. If `distinct` is `True`, call `QuerySet.distinct()`.
10. If `field_calculations` are not empty, run them and annotate their results to the `QuerySet`.
11. If `filters` is not empty, apply them using `QuerySet.filter()`
12. If `post_filter_callback` exists, call it.
13. If `pagination` data exists, run either `pagination.paginate_queryset()`
    or `pagination.paginate_prefetch_queryset()` depending on whether a `related_field` exists or not.
14. Return the optimized `QuerySet`.
