# Hacking Undine

While Undine aims to offer a batteries-included solution for
building GraphQL APIs on top of Django, it is designed to be
easy to modify and extend to suit the needs of any project.
For example, your project may include custom model fields,
or require dates or times to be parsed in a specific way.

## Converters

In this section, we will go through Undine's many converters,
which are implemented using _single-dispatch generic functions_.
A _singe-dispatch generic function_ is a function that has different implementations
based on the argument it receives. You can think of it as a dynamic switch statement.
You may know python [`@singledispatch`](https://peps.python.org/pep-0443/){:target="_blank"}
decorator from the standard library, which implements this pattern.
Undine implements its own version of it, which allows for more flexible dispatching.

This pattern allows users to override and extend the behavior of any
converter without having to modify Undine's code directly.
The different converters available are listed below.

### `convert_to_graphql_type`

This function is used to convert a value to a GraphQL input or output type.
For example, a `QueryType` `Field` may be based on a model field,
and so the `Field` needs to know which GraphQL type corresponds to the model's field.

In addition to the value to convert, the function also accepts a `model`
parameter, which is the Django model associated with the value, and a `is_input`
parameter, which is a boolean indicating whether the converter should return an input
or output type.

### `convert_to_graphql_argument_map`

This function is used to convert a value to a GraphQL argument map.
It's used by `Fields` and `Entrypoints` to figure out which
parameters their GraphQL fields should have. For example, if a `QueryType`
is used in a list `Entrypoint`, it should get its `FilterSet` and/or
`OrderSet` as arguments. Similarly, a `Connection` should get its
pagination arguments from this converter.

In addition to the value to convert, the function also accepts a `many`
parameter, which is a boolean indicating whether the converter should return
a list of arguments or not, and a `entrypoint` parameter, which is
a boolean indicating whether the converter is used in an `Entrypoint` or not.

### `convert_lookup_to_graphql_type`

This function is used to convert a lookup expression to a GraphQL type.
It's used in `Filters` to figure out the `Filter's` input type after the its
lookup expression has been added. For example a `__date` lookup changes the expected
input for a `DateTimeField` `Filter` from `DateTime` to `Date`.

In addition to the lookup expression to convert, the function also accepts a `default_type`
parameter, which is the default python type to use for the lookup, and a `many`
parameter, which is a boolean indicating whether the lookup is for a field that
contains a list of objects or not.

### `convert_to_python_type`

This function is used to convert a value to a Python type.
It has miscellaneous uses, for example in parsing model relation
info, or in [`convert_lookup_to_graphql_type`](#convert_lookup_to_graphql_type).

In addition to the value to convert, the function also accepts a `is_input`
parameter, which is a boolean indicating whether the converter should return
an input or output type.

### `convert_to_field_ref`

This function is used by `Fields` to handle their given reference.
Most of the time, registering an implementation for this converter
is only required to allow a new kind of `Field` reference to be used,
but may also be used to add optimizations or convert the reference
to a more general form (e.g. a string to a model field).

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Field` instance that is calling this function.
This allows the converter to access the `Field's` attributes however it
sees fit.

### `convert_to_input_ref`

This function is used by `Inputs` to handle their given reference.
Otherwise, it works the same as [`convert_to_field_ref`](#convert_to_field_ref).

### `convert_to_order_ref`

This function is used by `Orders` to handle their given reference.
Otherwise, it works the same as [`convert_to_field_ref`](#convert_to_field_ref).

### `convert_to_filter_ref`

This function is used by `Filters` to handle their given reference.
Otherwise, it works the same as [`convert_to_field_ref`](#convert_to_field_ref).

### `convert_to_field_resolver`

This function is used to convert a value to a GraphQL field resolver.
It's used by `Fields` to figure out which resolver function should be used
to resolve the field during a query. For example, related fields require
a different resolver from a regular field.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Field` instance that is calling this function.

### `convert_to_entrypoint_resolver`

This function is the `Entrypoint` equivalent of the
[`convert_to_field_resolver`](#convert_to_field_resolver) converter.
A separate converter is needed since `Entrypoints` may resolve differently
than `Fields`, or they can run the Optimizer.

### `convert_to_filter_resolver`

This function is used to convert a value to a `Filter` expression resolver.
This resolver receives the input of a `Filter` and returns a Django expression
used for filtering.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Filter` instance that is calling this function.

### `convert_to_description`

This function is used to convert a value to a GraphQL description.
It's used by `Fields`, `Inputs`, `Filters` and `Orders` to figure out
the description to use for their GraphQL types. For example, a the description
for a model field is it's `help_text` attribute.

### `convert_to_default_value`

This function is used to convert a value to a GraphQL default value.
It's used by `Inputs` to figure out the default value for their GraphQL
types. For example, a model field's default value is it's `default` attribute.
However, a default value is only added to an Input for a create mutation.

### `convert_to_bad_lookups`

This function is used to convert a given model field to a list of lookups
that are not supported by the field, even if a lookup is registered for it.

For example, if you check `BooleanField.get_lookups()`, it show many generic
lookups registered for the base `Field` class, which don't actually work
on a `BooleanField` (e.g. `contains` or `iendswith`). This function is used
to remove those lookups when auto-generating `Filters` for a `FilterSet`.

### `convert_to_field_complexity`

This function is used to convert a `Field` reference to its complexity value.
`Field's` complexity is used to limit the "size" of a query in order to prevent
requesting too much data in a single request. For example, model relations
have a complexity of 1, so that users do not query too many related objects
in a single request.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Field` instance that is calling this function.

### `is_field_nullable`

This function is used by `Fields` to determine whether their reference is nullable or not.
For example, a model field reference is nullable if it's `null` attribute is `True`.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Field` instance that is calling this function.

### `is_input_hidden`

This function is used by `Inputs` to determine whether their reference indicates
a hidden input, meaning an input that is not included in the schema.
For example, a model field can be hidden if it's `hidden` attribute is `True`,
for example for the reverse side of a `ForeignKey` that starts with a "+".

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Input` instance that is calling this function.

### `is_input_only`

This function is used by `Inputs` to determine whether their reference is only used for input,
or also saved on the model instance that is the target of the mutation.
For example, a non-model field is input-only since it doesn't get saved to the database.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Input` instance that is calling this function.

### `is_input_required`

This function is used by `Inputs` to determine whether their reference is required.
For example, a model field is required depending on the mutation it is used in,
if it has a default value, if it has `null=True`, etc.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Input` instance that is calling this function.

### `is_many`

This function is used to determine whether a value indicates a list of objects or not.
For example, a "many-to-many" field would return `True`.

In addition to the value to convert, the function also accepts a `model`
parameter, which is the Django model associated with the value, and a `name`
parameter, which is a name associated with the value (e.g. field name).

### `extend_expression`

This function is used to rewrite a Django expression as if it was referenced
from a given model field. For example, an `F` expression `F("name")` can be
rewritten to extend from `field_name` as `F("field_name__name")`, and similarly,
a `Q(name__exact="foo")` can be rewritten as `Q(field_name__name__exact="foo")`.
This is used by the optimizer to rewrite expressions from "to-one" fields
to the fields if the related model can be fetched using `select_related`.

In addition to the expression to convert, the function also accepts a `field_name`
parameter, which is the name of the field to extend the expression from.

## Registering implementations

To register new implementations for a converter, you need to decorate a
function using the `<converter>.register` method.

```python
-8<- "hacking_undine/registration_class.py"
```

With this implementation registered fo the `convert_to_graphql_type` converter,
calling `convert_to_graphql_type(str)` will return a `GraphQLString` object.
However, calling `convert_to_graphql_type("foo")` will not, since registration
distinguishes between types and instances of types.

A converter implementation should always accept `**kwargs: Any`, since those can
be used to pass any additional arguments required by the converter. For example,
the `convert_to_graphql_type` converter gets a `model` parameter, which indicates
the Django model associated with the value. With this, we could register a
different implementation for `str` that would return a GraphQL type based on the
model field with the given name.

```python
-8<- "hacking_undine/registration_instance.py"
```

If an implementation can be used for many different types, you can register it
using a type union.

```python
-8<- "hacking_undine/registration_union.py"
```

In a class hierarchy, you don't need to register implementations for all the
subclasses, if the implementation of a superclass is can be used for the child
class as well. Converters will automatically look up implementations based on the
method resolution order of a class if an implementation is not found for the
exact type.

```python
-8<- "hacking_undine/registration_mro.py"
```

Literal types can also be used, in which case an implementation is registered
for all the possible values of the literal type. When the converter is called
with a value which can be a literal value, the converter will first check
for any implementations for literals before checking for implementations for
the type itself.

```python
-8<- "hacking_undine/registration_literal.py"
```

If you need a different implementation for lambda functions as opposed to regular
functions, you can register an implementation for the special `Lambda` type.

```python
-8<- "hacking_undine/registration_lambda.py"
```

You can also register a default implementation for a converter using `Any`.
Usually this is not needed and should be left for Undine to handle, since
its likely you want an error to be raised by a converter for an unsupported
type.

## Supporting new references

Using the converters described above, we can extend the functionality of Undine objects
to support new references by registering new implementations for specific converters.
A new implementation might not be required for all converters if the new type
is a subtype of some existing type, which already has a implementation that works for it.

### Fields

Here are the converters that a new `Field` reference might need to implement:

1. [`convert_to_field_ref`](#convert_to_field_ref) to allow the new reference to be used in `Fields`.
2. [`convert_to_field_resolver`](#convert_to_field_resolver) to convert the reference to a resolver function.
3. [`convert_to_graphql_type`](#convert_to_graphql_type) to convert the reference to a GraphQL type.
4. [`convert_to_graphql_argument_map`](#convert_to_graphql_argument_map) to convert the reference to a GraphQL argument map.
5. [`convert_to_field_complexity`](#convert_to_field_complexity) to know the complexity of resolving the field.
6. [`convert_to_description`](#convert_to_description) to convert the reference to a description.
7. [`is_field_nullable`](#is_field_nullable) to know whether the reference is nullable or not.
8. [`is_many`](#is_many) to know whether the reference contains many objects or not.

### Inputs

Here are the converters that a new `Input` reference might need to implement:

1. [`convert_to_input_ref`](#convert_to_input_ref) to allow the new reference to be used in `Inputs`.
2. [`convert_to_graphql_type`](#convert_to_graphql_type) to convert the reference to a GraphQL type.
3. [`convert_to_default_value`](#convert_to_default_value) to determine the default value of the input.
4. [`convert_to_description`](#convert_to_description) to convert the reference to a description.
5. [`is_input_only`](#is_input_only) to know whether the reference is only used for input or not.
6. [`is_input_hidden`](#is_input_hidden) to know whether the reference is hidden from the schema or not.
7. [`is_input_required`](#is_input_required) to know whether the reference is required or not.
8. [`is_many`](#is_many) to know whether the reference contains many objects or not.

### Filters

Here are the converters that a new `Filter` reference might need to implement:

1. [`convert_to_filter_ref`](#convert_to_filter_ref) to allow the new reference to be used in `Filters`.
2. [`convert_to_filter_resolver`](#convert_to_filter_resolver) to convert the reference to a resolver function.
3. [`convert_to_graphql_type`](#convert_to_graphql_type) to convert the reference to a GraphQL type.
4. [`convert_to_description`](#convert_to_description) to convert the reference to a description.

### Orders

Here are the converters that a new `Order` reference might need to implement:

1. [`convert_to_order_ref`](#convert_to_order_ref) to allow the new reference to be used in `Orders`.
2. [`convert_to_description`](#convert_to_description) to convert the reference to a description.

### Interfaces

Here are the converters that a new `InterfaceType` reference might need to implement:

1. [`convert_to_graphql_type`](#convert_to_graphql_type) to convert the reference to a GraphQL type.
2. [`convert_to_graphql_argument_map`](#convert_to_graphql_argument_map) to convert the reference to a GraphQL argument map.
3. [`convert_to_entrypoint_resolver`](#convert_to_entrypoint_resolver) to convert the reference to a resolver function.

### Unions

Here are the converters that a new `UnionType` reference might need to implement:

1. [`convert_to_graphql_type`](#convert_to_graphql_type) to convert the reference to a GraphQL type.
2. [`convert_to_graphql_argument_map`](#convert_to_graphql_argument_map) to convert the reference to a GraphQL argument map.
3. [`convert_to_entrypoint_resolver`](#convert_to_entrypoint_resolver) to convert the reference to a resolver function.
