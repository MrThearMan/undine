description: Documentation on query ordering in Undine.

# Ordering

In this section, we'll cover the everything necessary for ordering
results returned by your [`QueryTypes`](queries.md#querytypes).

## OrderSet

An `OrderSet` is a collection of [`Order`](#order) objects that represents
an `Enum` in the GraphQL schema. When added to a `QueryType`,
it creates an input argument (as determined by the
[`QUERY_TYPE_ORDER_INPUT_KEY`](settings.md#query_type_order_input_key) setting)
on any list `Entrypoint` or many-related `Field` that is created using that `QueryType`.
That input can then be used to order the results returned by the `Entrypoint` or `Field`.

A basic `OrderSet` is created by subclassing `OrderSet`
and adding a Django Model to it as a generic type parameter.
You must also add at least one `Order` to the class body of the `OrderSet`.
Then, the `OrderSet` can be added to a `QueryType` using the `orderset` argument.

```python
-8<- "ordering/orderset_basic.py"
```

You can also add the `OrderSet` to the `QueryType` using decorator syntax.

```python
-8<- "ordering/orderset_decorator.py"
```

### Auto-generation

An `OrderSet` can automatically introspect its Django Model and convert the Model's fields
to `Orders` on the `OrderSet`.  For example, if the `Task` Model has the following fields:

```python
-8<- "ordering/models_1.py"
```

An auto-generated `OrderSet` has all of the `Task` Model's fields translated into GraphQL `Enum` values,
both in ascending and descending directions.

```graphql
enum TaskOrderSet {
  pkAsc
  pkDesc
  nameAsc
  nameDesc
  doneAsc
  doneDesc
  createdAtAsc
  createdAtDesc
}
```

To use auto-generation, either set [`AUTOGENERATION`](settings.md#autogeneration) setting to `True`
to enable it globally, or set the `auto` argument to `True` in the `OrderSet` class definition.
With this, you can leave the `OrderSet` class body empty.

```python
-8<- "ordering/orderset_auto.py"
```

Your can exclude some model fields from the auto-generation by setting the `exclude` argument:

```python
-8<- "ordering/orderset_exclude.py"
```

### Schema name

By default, the name of the generated GraphQL `Enum` for an `OrderSet` class
is the name of the `OrderSet` class. If you want to change the name separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "ordering/orderset_schema_name.py"
```

### Description

You can provide a description for the `OrderSet` by adding a docstring to the class.

```python
-8<- "ordering/orderset_description.py"
```

### Directives

You can add directives to an `OrderSet` by providing them using the `directives` argument.
The directive must be usable in the `ENUM` location.

```python
-8<- "ordering/orderset_directives.py"
```

You can also add directives using decorator syntax.

```python
-8<- "ordering/orderset_directives_decorator.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide an `OrderSet` from certain users by using the `__is_visible__` method.
Hiding the `OrderSet` means that it will not be included in introspection queries for that user,
and trying to use it in operations will result in an error that looks exactly like
the argument for the `OrderSet` didn't exist in the first place.

```python
-8<- "ordering/orderset_visible.py"
```

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL extensions

You can provide custom extensions for the `OrderSet` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `OrderSet`.

```python
-8<- "ordering/orderset_extensions.py"
```

`OrderSet` extensions are made available in the GraphQL `Enum` extensions
after the schema is created. The `OrderSet` itself is found in the GraphQL `Enum` extensions
under a key defined by the [`ORDERSET_EXTENSIONS_KEY`](settings.md#orderset_extensions_key)
setting.

## Order

An `Order` defines a way of ordering the results returned by an `Entrypoint` or `Field` using a `QueryType`.
An `Order` corresponds to anything that can be passed to a `queryset.order_by()` call,
usually a field on the Django Model of the `OrderSet` it belongs to.
In GraphQL, an `Order` represent two `EnumValues` on a GraphQL `Enum`,
one for ordering in ascending direction and one for ordering in descending direction.

An `Order` always requires a _**reference**_ which it will use to create the
Django `OrderBy` expression for the `Order`.

### Model field references

For `Orders` corresponding to Django Model fields, the `Order` can be used without passing in a reference,
as its attribute name in the `OrderSet` class body can be used to identify
the corresponding model field.

```python
-8<- "ordering/order.py"
```

To be a bit more explicit, you could use a string referencing the Model field:

```python
-8<- "ordering/order_string.py"
```

For better type safety, you can also use the Model field itself:

```python
-8<- "ordering/order_field.py"
```

Being explicit like this is only required if the name of the attribute in the GraphQL schema
is different from the Model field name.

```python
-8<- "ordering/order_alias.py"
```

### Expression references

Django ORM expressions can also be used as `Filter` references.

```python
-8<- "ordering/order_expression.py"
```

Remember that subqueries are also counted as expressions.

```python
-8<- "ordering/order_subquery.py"
```

### Null placement

If the Model field or expression used by the `Order` is nullable,
the `null_placement` argument can be used to specify the position of null values.

```python
-8<- "ordering/order_null_placement.py"
```

By default, null values are placed according to your database default.

### Aliases

Sometimes an `Order` may require additional expressions to be added as aliases
to the queryset when the `Order` is used. For this, you can define a function
that returns a dictionary of expressions and decorate it with the `aliases` decorator.

```python
-8<- "ordering/order_aliases.py"
```

### Field name

A `field_name` can be provided to explicitly set the Django Model field name
that the `Order` corresponds to.

```python
-8<- "ordering/order_field_name.py"
```

This can be useful when the Model field corresponding to the `Order`
has a different name and type in the GraphQL schema than on the Model.

### Schema name

By default, the name of the generated `Enum` values for an `Order` use the
name of the `Order` on the `OrderSet` class (converted to _camelCase_ if
[`CAMEL_CASE_SCHEMA_FIELDS`](settings.md#camel_case_schema_fields) is enabled)
as a base, with the full names having "Asc" and "Desc" suffixes added.
If you want to change the base name of the `Enum` value separately,
you can do so by setting the `schema_name` argument:

```python hl_lines="13"
-8<- "ordering/order_schema_name.py"
```

### Description

By default, an `Order` is able to determine its description based on its reference.
For example, for a [Model field](#model-field-references), the description is taken from its `help_text`.
If the reference has no description, or you wish to add a different one,
this can be done in two ways:

1) By setting the `description` argument.

```python
-8<- "ordering/order_description.py"
```

2) As class attribute docstrings, if [`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`](settings.md#enable_class_attribute_docstrings) is enabled.

```python
-8<- "ordering/order_description_class.py"
```

### Deprecation reason

A `deprecation_reason` can be provided to mark the `Order` as deprecated.
This is for documentation purposes only, and does not affect the use of the `Order`.

```python hl_lines="13"
-8<- "ordering/order_deprecation_reason.py"
```

### Directives

You can add directives to the `Order` by providing them using the `directives` argument.

```python
-8<- "ordering/order_directives.py"
```

You can also add them using the `@` operator (which kind of looks like GraphQL syntax):

```python
-8<- "ordering/order_directives_matmul.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide an `Order` from certain users by decorating a method with the
`<order_name>.visible` decorator. Hiding an `Order` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `Order` didn't exist in the first place.

```python
-8<- "ordering/order_visible.py"
```

### GraphQL extensions

You can provide custom extensions for the `Order` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `Order`.

```python
-8<- "ordering/order_extensions.py"
```

`Order` extensions are made available in the GraphQL `Enum` value extensions
after the schema is created. The `Order` itself is found in the Enum value extensions
under a key defined by the [`ORDER_EXTENSIONS_KEY`](settings.md#order_extensions_key)
setting.
