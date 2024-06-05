# Scalars

In this section, we'll cover how GraphQL scalars work in Undine.
Scalars are GraphQL types that represent concrete data types like
strings, numbers, and booleans.

## Built-in Scalars

In addition to GraphQL's built-in scalars of
[`Int`](https://spec.graphql.org/draft/#sec-Int){:target="_blank"},
[`Float`](https://spec.graphql.org/draft/#sec-Float){:target="_blank"},
[`String`](https://spec.graphql.org/draft/#sec-String){:target="_blank"},
[`Boolean`](https://spec.graphql.org/draft/#sec-Boolean){:target="_blank"},
and [`ID`](https://spec.graphql.org/draft/#sec-ID){:target="_blank"},
Undine provides its own scalars that are useful for representing common data types
in Python.

### `Any`

Represent any value accepted by GraphQL. Used for e.g. for union types.

### `Base16`

Represents a base16-encoded string as defined in
[RFC 4648](https://datatracker.ietf.org/doc/html/rfc4648#section-8){:target="_blank"}.

### `Base32`

Represents a base32-encoded string as defined in
[RFC 4648](https://datatracker.ietf.org/doc/html/rfc4648#section-8){:target="_blank"}.

### `Base64`

Represents a base64-encoded string as defined in
[RFC 4648](https://datatracker.ietf.org/doc/html/rfc4648#section-8){:target="_blank"}.

### `Date`

Represents a date value as specified by ISO 8601.
Maps to the Python `datetime.date` type.
See [RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339#section-5.6){:target="_blank"}.

### `DateTime`

Represents a date and time value as specified by ISO 8601.
Maps to the Python `datetime.datetime` type.
See [RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339#section-5.6){:target="_blank"}.

### `Decimal`

Represents a number as a string for correctly rounded floating point arithmetic.
Maps to the Python `decimal.Decimal` type.

### `Duration`

Represents a duration of time in seconds.
Maps to the Python `datetime.timedelta` type.

### `Email`

Represents a valid email address.
See [RFC 5322](https://datatracker.ietf.org/doc/html/rfc5322#section-3.4.1){:target="_blank"}.

### `File`

Represents any kind of file. See the [file upload](file-upload.md) section.


### `IP`

Represents a valid IPv4 or IPv6 address.
See [RFC 8200](https://datatracker.ietf.org/doc/html/rfc8200){:target="_blank"}.
and [RFC 791](https://datatracker.ietf.org/doc/html/rfc791){:target="_blank"}.

### `IPv4`

Represents a valid IPv4 address.
See [RFC 791](https://datatracker.ietf.org/doc/html/rfc791){:target="_blank"}.


### `IPv6`

Represents a valid IPv6 address.
See [RFC 8200](https://datatracker.ietf.org/doc/html/rfc8200){:target="_blank"}.

### `Image`

Represents an image file. See the [file upload](file-upload.md) section.

### `JSON`

Represents a JSON serializable object.
Maps to the Python `dict` type.
See [RFC 8259](https://datatracker.ietf.org/doc/html/rfc8259){:target="_blank"}.

### `Null`

Represents represents an always null value.
Maps to the Python `None` value.

### `Time`

Represents a time value as specified by ISO 8601.
Maps to the Python `datetime.time` type.
See [RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339#section-5.6){:target="_blank"}.

### `URL`

Represents a valid URL.
See [RFC 3986](https://datatracker.ietf.org/doc/html/rfc3986){:target="_blank"}.

### `UUID`

Represents a universally unique identifier string.
Maps to Python's `uuid.UUID` type.
See [RFC 9562](https://datatracker.ietf.org/doc/html/rfc9562){:target="_blank"}.

## Modifying existing scalars

All scalars have two functions that define its operation: `parse` and `serialize` These are used to
parse incoming data to python types and serialize python data to GraphQL accepted types respectively.

In Undine's additional built-in scalars, these functions are _single dispatch generic functions_.
This means that we can register different implementations for the functions which are called
depending on the type of the input value — think of it like a dynamic switch statement.
This allows us to replace or extend the behavior of a scalar depending on our use case.

For example, we might want to use the [whenever]{:target="_blank"} library instead
or in addition to python's built-in `datetime`. To do this, we can register a new
implementation for the `parse` function of the `DateTime` scalar.

[whenever]: https://github.com/ariebovenberg/whenever

```python
-8<- "scalars/scalar_modify.py"
```

## Custom scalars

We can also define our own scalars to represent types that cannot be represented
by any of Undine's built-in scalars. Let's create a new scalar named `Vector3`
that represents a 3D vector using a tuple of three integers.

```python
-8<- "scalars/custom_scalar.py"
```

If `Vector3` corresponds to a Django model field, we could also let Undine know
about it by registering it for its many built-in converters. This way a model field
can be converted automatically to our scalar for `QueryType` `Fields` and `MutationType` `Inputs`.
More on this in the ["Hacking Undine"](hacking-undine.md) section.
