description: Hacking Undine with converters.

# Hacking Undine

While Undine aims to offer a batteries-included solution for
building GraphQL APIs on top of Django, it is designed to be
easy to modify and extend to suit the needs of any project.
For example, your project may include custom Model fields,
or require dates or times to be parsed in a specific way.

## Converters

In this section, we will go through Undine's many converters,
which are used by Undine to process values in various parts of its objects.
These converters are implemented using _single-dispatch generic functions_.
A _singe-dispatch generic function_ is a function that has different implementations
based on the type of the argument it receives. You can think of it as a dynamic switch statement.
You may know the [`@singledispatch`][singledispatch]{:target="_blank"}
decorator from the python standard library, which implements this pattern.
Undine implements its own version of it, which allows for more flexible dispatching.

[singledispatch]: https://peps.python.org/pep-0443/

This pattern allows users to override and extend the behavior of any
converter without having to modify Undine's code directly.
The different converters available are listed below.

### `convert_to_graphql_type`

This function is used to convert a value to a GraphQL input or output type.
For example, a `QueryType` `Field` may be based on a model field,
and so the `Field` needs to know which GraphQL type corresponds to the model's field.

In addition to the value to convert, the function also accepts a `model`
parameter, which is the Django Model associated with the value, and a `is_input`
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
parameter, which is the GraphQLType for the parent field the lookup is for.

### `convert_to_model_field_to_python_type`

This function is used to convert a model fields to a Python type.
It's used in parsing Model relation types, which are used by
various parts of Undine when working with Model relations.

### `convert_to_entrypoint_ref`

This function is used by `Entrypoints` to handle their given reference.
Most of the time, registering an implementation for this converter
is only required to allow a new kind of `Entrypoint` reference to be used,
but may also be used to add additional handling for the reference.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Entrypoint` instance that is calling this function.
This allows the converter to access the `Entrypoint's` attributes however it
sees fit.

### `convert_to_field_ref`

This function is used by `Fields` to handle their given reference.
Otherwise, it works the same as [`convert_to_entrypoint_ref`](#convert_to_entrypoint_ref),
with the `caller` parameter set to the `Field` instance.

### `convert_to_input_ref`

This function is used by `Inputs` to handle their given reference.
Otherwise, it works the same as [`convert_to_entrypoint_ref`](#convert_to_entrypoint_ref),
with the `caller` parameter set to the `Input` instance.

### `convert_to_order_ref`

This function is used by `Orders` to handle their given reference.
Otherwise, it works the same as [`convert_to_entrypoint_ref`](#convert_to_entrypoint_ref),
with the `caller` parameter set to the `Order` instance.

### `convert_to_filter_ref`

This function is used by `Filters` to handle their given reference.
Otherwise, it works the same as [`convert_to_entrypoint_ref`](#convert_to_entrypoint_ref),
with the `caller` parameter set to the `Filter` instance.

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
It's used by `Filters` to figure out which resolver function should be used
for filtering. A `Filter` resolver function always returns a Django expression.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Filter` instance that is calling this function.

### `convert_to_entrypoint_subscription`

This function is used to convert a value to a GraphQL subscription resolver.
It's used by `Entrypoints` to figure out which resolver function should be used
for subscriptions.

### `convert_to_description`

This function is used to convert a value to a GraphQL description.
It's used by `Fields`, `Inputs`, `Filters` and `Orders` to figure out
the description to use for their GraphQL types. For example, the description
for a Model field is its `help_text` attribute.

### `convert_to_default_value`

This function is used to convert a value to a GraphQL default value.
It's used by `Inputs` to figure out the default value for their GraphQL
types. For example, a Model field's default value is its `default` attribute.
However, a default value is only added to an Input for a create mutation.

### `convert_to_bad_lookups`

This function is used to convert a given Model field to a list of lookups
that are not supported by the field, even if the given lookup is registered for it.

For example, if you check `BooleanField.get_lookups()`, it show many generic
lookups registered for the base `Field` class, which don't actually work
on a `BooleanField` (e.g. `contains` or `iendswith`). This function is used
to remove those lookups when auto-generating `Filters` for a `FilterSet`.

### `convert_to_field_complexity`

This function is used to convert a `Field` reference to its [complexity](queries.md#complexity) value.
By default, any reference passed to it has a complexity of 0 if not specified.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Field` instance that is calling this function.

### `is_field_nullable`

This function is used by `Fields` to determine whether their reference is nullable or not.
For example, a Model field reference is nullable if its `null` attribute is `True`.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Field` instance that is calling this function.

### `is_input_hidden`

This function is used by `Inputs` to determine whether their reference indicates
a hidden input, meaning an input that is not included in the schema.
For example, a Model field can be hidden if its `hidden` attribute is `True`,
for example for the reverse side of a `ForeignKey` that starts with a "+".

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Input` instance that is calling this function.

### `is_input_only`

This function is used by `Inputs` to determine whether their reference is only used for input,
or also saved on the Model instance that is the target of the mutation.
For example, a non-Model field is input-only since it doesn't get saved to the database.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Input` instance that is calling this function.

### `is_input_required`

This function is used by `Inputs` to determine whether their reference is required.
For example, a Model field is required depending on the mutation it's used in,
if it has a default value, if it has `null=True`, etc.

In addition to the value to convert, the function also accepts a `caller`
parameter, which is the `Input` instance that is calling this function.

### `is_many`

This function is used to determine whether a value indicates a list of objects or not.
For example, a "many-to-many" field would return `True`.

In addition to the value to convert, the function also accepts a `model`
parameter, which is the Django Model associated with the value, and a `name`
parameter, which is a name associated with the value (e.g. field name).

### `extend_expression`

This function is used to rewrite a Django expression as if it was referenced
from a given Model field. For example, an `F` expression `F("name")` can be
rewritten to extend from `field_name` as `F("field_name__name")`, and similarly,
a `Q(name__exact="foo")` can be rewritten as `Q(field_name__name__exact="foo")`.
This is used by the optimizer to rewrite expressions from "to-one" fields
to the fields if the related Model can be fetched using `select_related`.

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
distinguishes between types and instances of types. To register for an instance,
do this instead:

```python
-8<- "hacking_undine/registration_instance.py"
```

A converter implementation should always accept `**kwargs: Any`, since those can
be used to pass any additional arguments required by the converter. For example,
the `convert_to_graphql_type` converter gets a `model` parameter, which indicates
the Django model associated with the value.

If an implementation can be used for many different types, you can register it
using a type union.

```python
-8<- "hacking_undine/registration_union.py"
```

If the implementation of a superclass is can be used for a child class,
you don't need to register implementations for the child class.
Converters will automatically look up implementations based on the
method resolution order of a class if an implementation is not found for the
exact type.

```python
-8<- "hacking_undine/registration_mro.py"
```

Implementations can be registered for literal values as well,
in which case an implementation is registered for all the possible values of the `Literal`.
When the converter is called with a value which can be a literal value, the converter will first check
for any implementations for literals before checking for implementations for the type itself.

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

### Entrypoints

Here are the converters that a new `Entrypoint` reference might need to implement:

1. [`convert_to_entrypoint_ref`](#convert_to_entrypoint_ref) to allow the new reference to be used in `Entrypoints`.
2. [`convert_to_entrypoint_resolver`](#convert_to_entrypoint_resolver) to convert the reference to a resolver function.
3. [`convert_to_graphql_type`](#convert_to_graphql_type) to convert the reference to a GraphQL type.
4. [`convert_to_graphql_argument_map`](#convert_to_graphql_argument_map) to convert the reference to a GraphQL argument map.
5. [`convert_to_entrypoint_subscription`](#convert_to_entrypoint_subscription) to convert the reference to a GraphQL subscription resolver function.
6. [`convert_to_description`](#convert_to_description) to convert the reference to a description.

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
