description: Documentation on query filtering in Undine.

# Filtering

In this section, we'll cover the everything necessary for filtering
results returned by your [`QueryTypes`](queries.md#querytypes).

## FilterSet

A `FilterSet` is a collection of [`Filter`](#filter) objects that represents
an `InputObjectType` in the GraphQL schema. When added to a `QueryType`,
it creates an input argument (as determined by the
[`QUERY_TYPE_FILTER_INPUT_KEY`](settings.md#query_type_filter_input_key) setting)
on any list `Entrypoint` or many-related `Field` that is created using that `QueryType`.
That input can then be used to filter the results returned by the `Entrypoint` or `Field`.

A basic `FilterSet` is created by subclassing `FilterSet`
and adding a Django Model to it as a generic type parameter.
You must also add at least one `Filter` to the class body of the `FilterSet`.
Then the `FilterSet` can be added to a `QueryType` using the `filterset` argument.

```python
-8<- "filtering/filterset_basic.py"
```

You can also add the `FilterSet` to the `QueryType` using decorator syntax.

```python
-8<- "filtering/filterset_decorator.py"
```

### Auto-generation

A `FilterSet` can automatically introspect its Django Model and convert the Model's fields
to `Filters` on the `FilterSet`. For example, if the `Task` model has the following fields:

```python
-8<- "filtering/models_1.py"
```

An auto-generated `FilterSet` will have all of the `Task` Model's fields and those fields'
lookups translated into input arguments.

/// details | Here is the generated `InputObjectType`

```graphql
input TaskFilterSet {
  createdAt: DateTime
  createdAtDate: Date
  createdAtDateGt: Date
  createdAtDateGte: Date
  createdAtDateIn: [Date!]
  createdAtDateLt: Date
  createdAtDateLte: Date
  createdAtDateRange: [Date!]
  createdAtDay: Int
  createdAtDayContains: Int
  createdAtDayEndsWith: Int
  createdAtDayGt: Int
  createdAtDayGte: Int
  createdAtDayIn: [Int!]
  createdAtDayLt: Int
  createdAtDayLte: Int
  createdAtDayRange: [Int!]
  createdAtDayStartsWith: Int
  createdAtGt: DateTime
  createdAtGte: DateTime
  createdAtHour: Int
  createdAtHourContains: Int
  createdAtHourEndsWith: Int
  createdAtHourGt: Int
  createdAtHourGte: Int
  createdAtHourIn: [Int!]
  createdAtHourLt: Int
  createdAtHourLte: Int
  createdAtHourRange: [Int!]
  createdAtHourStartsWith: Int
  createdAtIn: [DateTime!]
  createdAtIsoWeekDay: Int
  createdAtIsoWeekDayContains: Int
  createdAtIsoWeekDayEndsWith: Int
  createdAtIsoWeekDayGt: Int
  createdAtIsoWeekDayGte: Int
  createdAtIsoWeekDayIn: [Int!]
  createdAtIsoWeekDayLt: Int
  createdAtIsoWeekDayLte: Int
  createdAtIsoWeekDayRange: [Int!]
  createdAtIsoWeekDayStartsWith: Int
  createdAtIsoYear: Int
  createdAtIsoYearContains: Int
  createdAtIsoYearEndsWith: Int
  createdAtIsoYearGt: Int
  createdAtIsoYearGte: Int
  createdAtIsoYearIn: [Int!]
  createdAtIsoYearLt: Int
  createdAtIsoYearLte: Int
  createdAtIsoYearRange: [Int!]
  createdAtIsoYearStartsWith: Int
  createdAtLt: DateTime
  createdAtLte: DateTime
  createdAtMinute: Int
  createdAtMinuteContains: Int
  createdAtMinuteEndsWith: Int
  createdAtMinuteGt: Int
  createdAtMinuteGte: Int
  createdAtMinuteIn: [Int!]
  createdAtMinuteLt: Int
  createdAtMinuteLte: Int
  createdAtMinuteRange: [Int!]
  createdAtMinuteStartsWith: Int
  createdAtMonth: Int
  createdAtMonthContains: Int
  createdAtMonthEndsWith: Int
  createdAtMonthGt: Int
  createdAtMonthGte: Int
  createdAtMonthIn: [Int!]
  createdAtMonthLt: Int
  createdAtMonthLte: Int
  createdAtMonthRange: [Int!]
  createdAtMonthStartsWith: Int
  createdAtQuarter: Int
  createdAtQuarterContains: Int
  createdAtQuarterEndsWith: Int
  createdAtQuarterGt: Int
  createdAtQuarterGte: Int
  createdAtQuarterIn: [Int!]
  createdAtQuarterLt: Int
  createdAtQuarterLte: Int
  createdAtQuarterRange: [Int!]
  createdAtQuarterStartsWith: Int
  createdAtRange: [DateTime!]
  createdAtSecond: Int
  createdAtSecondContains: Int
  createdAtSecondEndsWith: Int
  createdAtSecondGt: Int
  createdAtSecondGte: Int
  createdAtSecondIn: [Int!]
  createdAtSecondLt: Int
  createdAtSecondLte: Int
  createdAtSecondRange: [Int!]
  createdAtSecondStartsWith: Int
  createdAtTime: Time
  createdAtTimeContains: Time
  createdAtTimeEndsWith: Time
  createdAtTimeGt: Time
  createdAtTimeGte: Time
  createdAtTimeIn: [Time!]
  createdAtTimeLt: Time
  createdAtTimeLte: Time
  createdAtTimeRange: [Time!]
  createdAtTimeStartsWith: Time
  createdAtWeek: Int
  createdAtWeekContains: Int
  createdAtWeekDay: Int
  createdAtWeekDayContains: Int
  createdAtWeekDayEndsWith: Int
  createdAtWeekDayGt: Int
  createdAtWeekDayGte: Int
  createdAtWeekDayIn: [Int!]
  createdAtWeekDayLt: Int
  createdAtWeekDayLte: Int
  createdAtWeekDayRange: [Int!]
  createdAtWeekDayStartsWith: Int
  createdAtWeekEndsWith: Int
  createdAtWeekGt: Int
  createdAtWeekGte: Int
  createdAtWeekIn: [Int!]
  createdAtWeekLt: Int
  createdAtWeekLte: Int
  createdAtWeekRange: [Int!]
  createdAtWeekStartsWith: Int
  createdAtYear: Int
  createdAtYearContains: Int
  createdAtYearEndsWith: Int
  createdAtYearGt: Int
  createdAtYearGte: Int
  createdAtYearIn: [Int!]
  createdAtYearLt: Int
  createdAtYearLte: Int
  createdAtYearRange: [Int!]
  createdAtYearStartsWith: Int
  done: Boolean
  name: String
  nameContains: String
  nameContainsExact: String
  nameEndsWith: String
  nameEndsWithExact: String
  nameExact: String
  nameIn: [String!]
  nameStartsWith: String
  nameStartsWithExact: String
  pk: Int
  pkContains: Int
  pkEndsWith: Int
  pkGt: Int
  pkGte: Int
  pkIn: [Int!]
  pkLt: Int
  pkLte: Int
  pkRange: [Int!]
  pkStartsWith: Int
  project: Int
  projectGt: Int
  projectGte: Int
  projectIn: [Int!]
  projectIsNull: Boolean
  projectLt: Int
  projectLte: Int
  NOT: TaskFilterSet
  AND: TaskFilterSet
  OR: TaskFilterSet
  XOR: TaskFilterSet
}
```

///

/// details | About `Filter` names

Usually the names of the `Filters` generated by auto-generation correspond to the lookup
in Django, but for text-based fields, names are changed slightly to lean towards using
case-insensitive lookups first: Filter `name` uses `__iexact` and `nameExact` uses `__exact`.
Similarly, `nameStartsWith` uses `__istartswith` while `nameStartsWithExact` uses `__startswith`, etc.

///

To use auto-generation, either set [`AUTOGENERATION`](settings.md#autogeneration) setting to `True`
to enable it globally, or set the `auto` argument to `True` in the `FilterSet` class definition.
With this, you can leave the `FilterSet` class body empty.

```python
-8<- "filtering/filterset_auto.py"
```

You can exclude some Model fields from the auto-generation by setting the `exclude` argument:

```python
-8<- "filtering/filterset_exclude.py"
```

You can also exclude specific model lookups, e.g. `created_at__gte`.

### Logical operators

A `FilterSet` always provides the logical operators `NOT`, `AND`, `OR`, `XOR`,
allowing users to freely create more complex filter conditions from defined `Filters`.
Let's assume you've added an [auto-generated](#auto-generation) `TaskFilterSet`
for a `QueryType` named `TaskType`. Normally, when multiple `Filters` are used,
you'll get results that match all filter conditions.

```graphql
query {
  tasks(
    filter: {
      nameStartsWith: "a"
      done: true
    }
  ) {
    name
  }
}
```

By putting the filter conditions inside an `OR` block,
we can get results that match any of the conditions.

```graphql
query {
  tasks(
    filter: {
      OR: {
        nameStartsWith: "a"
        done: true
      }
    }
  ) {
    name
  }
}
```

Note that only the results _inside_ the conditional block will use that logical combinator.
For example, in the following example, only tasks that contains an "e" AND EITHER start with "a"
OR are done will be returned:

```graphql
query {
  tasks(
    filter: {
      nameContains: "e"
      OR: {
        nameStartsWith: "a"
        done: true
      }
    }
  ) {
    name
  }
}
```

### Filter queryset

In addition to [`Filters`](#filter), `FilterSet` also includes a `__filter_queryset__`
classmethod, which can be used to add filtering that should always be applied
when fetching objects through `QueryTypes` using the given `FilterSet`.

```python
-8<- "filtering/filterset_filter_queryset.py"
```

Note that `QueryTypes` also have a `__filter_queryset__` classmethod, which is run _before_
any `FilterSet` `Filters`, and that `FilterSet's` `__filter_queryset__` is run _after_.
See the Optimizer's [order of operations](optimizer.md#order-of-optimizations) for more details.

### Schema name

By default, the name of the generated GraphQL `InputObjectType` for a `FilterSet` class
is the name of the `FilterSet` class. If you want to change the name separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "filtering/filterset_schema_name.py"
```

### Description

You can provide a description for a `FilterSet` by adding a docstring to the class.

```python
-8<- "filtering/filterset_description.py"
```

### Directives

You can add directives to a `FilterSet` by providing them using the `directives` argument.
The directive must be usable in the `INPUT_OBJECT` location.

```python
-8<- "filtering/filterset_directives.py"
```

You can also add directives using decorator syntax.

```python
-8<- "filtering/filterset_directives_decorator.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide a `FilterSet` from certain users by using the `__is_visible__` method.
Hiding the `FilterSet` means that it will not be included in introspection queries for that user,
and trying to use it in operations will result in an error that looks exactly like
the argument for the `FilterSet` didn't exist in the first place.

```python
-8<- "filtering/filterset_visible.py"
```

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL extensions

You can provide custom extensions for the `FilterSet` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `FilterSet`.

```python
-8<- "filtering/filterset_extensions.py"
```

`FilterSet` extensions are made available in the GraphQL `InputObjectType` extensions
after the schema is created. The `FilterSet` itself is found in the GraphQL `InputObjectType` extensions
under a key defined by the [`FILTERSET_EXTENSIONS_KEY`](settings.md#filterset_extensions_key)
setting.

## Filter

A `Filter` defines a way of filtering the results returned by an `Entrypoint` or `Field` using a `QueryType`.
A `Filter` corresponds to anything that can be passed to a `queryset.filter()` call,
usually a [lookup expression] on the Django Model of the `FilterSet` it belongs to.
In GraphQL, a `Filter` represents a `GraphQLInputField` on an `InputObjectType`.

[lookup expression]: https://docs.djangoproject.com/en/stable/topics/db/queries/#field-lookups

A `Filter` always requires a _**reference**_ from which it will create the proper GraphQL resolver
and input type for the `Filter`.

### Model field references

For `Filters` corresponding to Django Model fields, the `Filter` can be used without passing in a reference,
as its attribute name on the `FilterSet` class body can be used to identify
the corresponding Model field.

```python
-8<- "filtering/filter.py"
```

To be a bit more explicit, you could use a string referencing the Model field:

```python
-8<- "filtering/filter_string.py"
```

For better type safety, you can also use the Model field itself:

```python
-8<- "filtering/filter_field.py"
```

Being explicit like this is only required if the name of the attribute in the GraphQL schema
is different from the Model field name.

```python
-8<- "filtering/filter_alias.py"
```

### Expression references

Django ORM expressions can also be used as `Filter` references.

```python
-8<- "filtering/filter_expression.py"
```

Remember that subqueries are also counted as expressions.

```python
-8<- "filtering/filter_subquery.py"
```

### Function references

Functions (or methods) can also be used to create `Filters`.
This can be done by decorating a method with the `Filter` class.

```python
-8<- "filtering/filter_decorator.py"
```

These types of `Filters` should return a `Q` expression.
The type of the `value` argument is used as the input type for the `Filter`, so typing it is required.

/// details | About method signature

The decorated method is treated as a static method by the `Filter`.

The `self` argument is not an instance of the `FilterSet`,
but the instance of the `Filter` that is being used.

The `info` argument can be left out, but if it's included, it should always
have the `GQLInfo` type annotation.

The `value` argument is the value provided for the filter. It should always be named "value",
and is required to be a keyword only argument.

///

### Lookup

By default, when a `Filter` is defined on a `FilterSet`, the "exact" [lookup expression]
is used. This can be changed by providing the `lookup` argument to the `Filter`.

[lookup expression]: https://docs.djangoproject.com/en/stable/ref/models/querysets/#field-lookups

```python
-8<- "filtering/filter_lookup.py"
```

### Many

The `many` argument changes the behavior of a `Filter` such that it takes
a list of values instead of a single value. Then, each of the given values are combined
as defined by the [`match`](#match) argument to form a single filter condition.

```python
-8<- "filtering/filter_many.py"
```

This would create the following filter input:

```graphql
input TaskFilterSet {
  name: [String!]
}
```

So if a query is filtered using this filter with the value `["foo", "bar"]`,
the filter condition would be `Q(name__icontains="foo") | Q(name__icontains="bar")`.

### Match

The `match` argument changes the behavior of the [`many`](#many) argument to combine the
provided values with a different operation. The default is `any`, which means
that the filter condition will include an item if it matches any of the provided values.

The `match` argument can be set to `all` if all of the values should match,
or `one_of` if only one of the values should match.

```python
-8<- "filtering/filter_match.py"
```

### Distinct

If using a `Filter` would require a call to `queryset.distinct()` to remove duplicates
(e.g. lookups spanning "to-many" relations), you can set the `distinct` argument to `True`.

```python
-8<- "filtering/filter_distinct.py"
```

### Required

By default, all `Filters` are non-required (nullable in GraphQL terms).
If you want to make a `Filter` required, you can do so by setting the `required` argument to `True`.

```python
-8<- "filtering/filter_required.py"
```

Making a `Filter` required means that if any filtering is done on an `Entrypoint` of related `Field`
using a `QueryType` with the `FilterSet` this `Filter` belongs to, this `Filter` must be used in
addition to any other `Filters` you might want to use. It must also be used in any logical
blocks that users might want to make.

### Aliases

Sometimes a `Filter` may require additional expressions to be added as aliases
to the queryset when the `Filter` is used. For this, you can define a function
that returns a dictionary of expressions and decorate it with the `aliases` decorator.

```python
-8<- "filtering/filter_aliases.py"
```

### Empty values

By default, `Filters` will ignore some values which are considered _"empty"_ in the context of filtering.
These values are set globally by the [`EMPTY_VALUES`](settings.md#empty_values) setting.
Usually this is what you want, as it allows you to set default values in your GraphQL variables.

If you wish to change what's considered an empty value for an individual `Filter`,
you can do so by setting the `empty_values` argument to a list of values.

```python
-8<- "filtering/filter_empty_values.py"
```

### Field name

A `field_name` can be provided to explicitly set the Django Model field
that the `Filter` corresponds to.

```python
-8<- "filtering/filter_field_name.py"
```

This can be useful when the Model field corresponding to the `Filter`
has a different name and type in the GraphQL schema than in the Model.

### Schema name

By default, the name of the `InputObjectType` field generated from a `Filter` is the same
as the name of the `Filter` on the `FilterSet` class (converted to _camelCase_ if
[`CAMEL_CASE_SCHEMA_FIELDS`](settings.md#camel_case_schema_fields) is enabled).
If you want to change the name of the `InputObjectType` field separately,
you can do so by setting the `schema_name` argument:

```python hl_lines="13"
-8<- "filtering/filter_schema_name.py"
```

This can be useful when the desired name of the `InputObjectType` field is a Python keyword
and cannot be used as the `Input` attribute name.

### Description

By default, a `Filter` is able to determine its description based on its reference.
For example, for a [Model field](#model-field-references), the description is taken from its `help_text`.
If the reference has no description, or you wish to add a different one,
this can be done in two ways:

1) By setting the `description` argument.

```python
-8<- "filtering/filter_description.py"
```

2) As class attribute docstrings, if [`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`](settings.md#enable_class_attribute_docstrings) is enabled.

```python
-8<- "filtering/filter_description_class.py"
```

When using [function references](#function-references), instead of a class attribute docstring,
you add a docstring to the function/method used as the reference instead.

```python
-8<- "filtering/filter_decorator_docstring.py"
```

### Deprecation reason

A `deprecation_reason` can be provided to mark the `Filter` as deprecated.
This is for documentation purposes only, and does not affect the use of the `Filter`.

```python hl_lines="13"
-8<- "filtering/filter_deprecation_reason.py"
```

### Permissions

You can add permissions check to individual `Filters` by using `Filter` [functions](#function-references)
and adding the permission check inline.

```python
-8<- "filtering/filter_permissions.py"
```

A special `EmptyFilterResult` exception can also be raised to indicate that
an empty queryset should be returned instead of an error.

```python
-8<- "filtering/filter_empty_filter_result.py"
```

### Directives

You can add directives to the `Filter` by providing them using the `directives` argument.

```python
-8<- "filtering/filter_directives.py"
```

You can also add them using the `@` operator (which kind of looks like GraphQL syntax):

```python
-8<- "filtering/filter_directives_matmul.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide a `Filter` from certain users by decorating a method with the
`<filter_name>.visible` decorator. Hiding a `Filter` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `Filter` didn't exist in the first place.

```python
-8<- "filtering/filter_visible.py"
```

### GraphQL extensions

You can provide custom extensions for the `Filter` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `Filter`.

```python
-8<- "filtering/filter_extensions.py"
```

`Filter` extensions are made available in the GraphQL `InputObjectType` field extensions
after the schema is created. The `Filter` itself is found in the GraphQL input field extensions
under a key defined by the [`FILTER_EXTENSIONS_KEY`](settings.md#filter_extensions_key)
setting.
