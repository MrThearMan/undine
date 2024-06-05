# Ordering

In this section, we'll cover the everything necessary for adding ordering
for your [`QueryTypes`](queries.md#querytypes).

## OrderSet

An `OrderSet` is a collection of [`Order`](#order) objects that can be applied to a
[`QueryType`](queries.md#querytypes). In GraphQL, they represent a GraphQL `Enum`, which
when added to a `QueryType` creates an input argument for ordering the results of a `QueryType`.

A basic `OrderSet` is created by subclassing `OrderSet`
and adding its Django Model as a generic type parameter:

```python
-8<- "ordering/orderset_basic.py"
```

### Auto-generation

By default, an `OrderSet` automatically introspects its model and converts the model's fields
to input fields on the generated `Enum`. Given the following models:

```python
-8<- "ordering/models_1.py"
```

Simply subclassing `OrderSet` creates the following `Enum`:

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

This `Enum` has all of the `Task` model's fields translated into `Enum` values,
both in ascending and descending directions. With this, you can
freely create any ordering you want by combining the different enum values.

```graphql
query {
  tasks(
    orderBy: [
      pkAsc
      nameDesc
    ]
  ) {
    name
  }
}
```

This will order the `Task` objects by their primary key in ascending order,
and then by their name in descending order.

You can disable auto-generation by setting the `auto` argument to `False` in the class definition:

```python
-8<- "ordering/orderset_no_auto.py"
```

Alternatively, you could exclude some `Orders` from the auto-generation by setting the `exclude` argument:

```python
-8<- "ordering/orderset_exclude.py"
```

### Schema name

By default, the name of the generated `Enum` is the same as the name of the `OrderSet` class.
If you want to change the name, you can do so by setting the `schema_name` argument:

```python
-8<- "ordering/orderset_schema_name.py"
```

### Description

You can provide a description using the `description` argument.

```python
-8<- "ordering/orderset_description.py"
```

### Directives

You can add directives to the `OrderSet` by providing them using the `directives` argument.

```python
-8<- "ordering/orderset_directives.py"
```

See the [Directives](directives.md) section for more details on directives.

### GraphQL extensions

You can provide custom extensions for the `OrderSet` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `OrderSet`.

```python
-8<- "ordering/orderset_extensions.py"
```

`OrderSet` extensions are made available in the GraphQL `Enum` extensions
after the schema is created. The `OrderSet` itself is found in the `extensions`
under a key defined by the `ORDERSET_EXTENSIONS_KEY` setting.

## Order

An `Order` is a class that is used to define a possible ordering for an `OrderSet`.
Usually `Orders` correspond to fields on the Django model for their respective `OrderSet`.
In GraphQL, it represents an `EnumValue` in a GraphQL `Enum`.

An `Order` always requires a _**reference**_ which it will use to create the
Django `OrderBy` expression for the `Order`.

### Model field references

As seen in the [`OrderSet`](#orderset) section, you don't need to provide model fields
explicitly thanks to [auto-generation](#auto-generation), but if you wanted to be more explicit,
you could add the `Orders` to the `OrderSet` class body. In this case, the `Order` can be used
without a reference, as its attribute name in the `OrderSet` class body can be used to identify
the corresponding model field.

```python
-8<- "ordering/order.py"
```

To be a bit more explicit, you could use a string referencing the model field:

```python
-8<- "ordering/order_string.py"
```

For better type safety, you can also use the model field itself:

```python
-8<- "ordering/order_field.py"
```

Being explicit like this is only required if the name of the attribute in the GraphQL schema
is different from the model field name.

```python
-8<- "ordering/order_alias.py"
```

### Expression references

Django ORM expressions can also be used as the references.

```python
-8<- "ordering/order_expression.py"
```

Remember that subqueries are also counted as expressions.

```python
-8<- "ordering/order_subquery.py"
```

### Null placement

If the model field or expression used by the `Order` is nullable,
the `null_placement` argument can be used to specify the position of null values.

```python
-8<- "ordering/order_null_placement.py"
```

By default, null values are placed according to your database default.

### Field name

A `field_name` can be provided to explicitly set the Django model field name
that the `Order` corresponds to. This can be useful when the field has a different
name and type in the GraphQL schema than in the model.

```python
-8<- "ordering/order_field_name.py"
```

### Schema name

A `schema_name` can be provided to override the name of the `Order` in the GraphQL schema.
This can be useful for renaming fields for the schema, or when the desired name is a Python keyword
and cannot be used as the `Order` attribute name.

```python hl_lines="13"
-8<- "ordering/order_schema_name.py"
```

### Description

By default, an `Order` is able to determine its description based on its reference.
For example, for a model field, the description is taken from its `help_text`.

If the reference has no description, or you wish to add a different one,
this can be done in two ways:

1) By setting the `description` argument.

```python
-8<- "ordering/order_description.py"
```

2) As class variable docstrings.

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

See the [Directives](directives.md) section for more details on directives.

### GraphQL extensions

You can provide custom extensions for the `Order` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `Order`.

```python
-8<- "ordering/order_extensions.py"
```

`Order` extensions are made available in the GraphQL `Enum` value extensions
after the schema is created. The `Order` itself is found in the `extensions`
under a key defined by the `ORDER_EXTENSIONS_KEY` setting.
