from django.core.exceptions import ValidationError

from undine.scalars import ScalarType

Vector3 = tuple[int, int, int]

# Create a new ScalarType for our custom scalar.
# In `ScalarType[Vector3, str]`, the first type parameter is the type that
# the scalar will parse to, and the second the type that it will serialize to.
vector3_scalar: ScalarType[Vector3, str] = ScalarType(
    name="Vector3",
    description="Represents a 3D vector as a string in format 'X,Y,Z'.",
)

# Create the GraphQLScalarType from graphql-core.
# This is the actual scalar we can add to our schema.
GraphQLVector3 = vector3_scalar.as_graphql_scalar()


# Register the parse and serialize functions for our scalar.
@vector3_scalar.parse.register
def _(value: str) -> Vector3:
    try:
        x, y, z = value.split(",")
        return int(x.strip()), int(y.strip()), int(z.strip())

    except ValueError as error:
        msg = f"Invalid vector format: {value}"
        raise ValidationError(msg) from error


@vector3_scalar.serialize.register
def _(value: tuple) -> str:
    if len(value) != 3:
        msg = f"Vector must have 3 components, got {len(value)}"
        raise ValidationError(msg)

    if not isinstance(value[0], int):
        msg = f"Vector component X is not an integer, got {value[0]}"
        raise ValidationError(msg)

    if not isinstance(value[1], int):
        msg = f"Vector component Y is not an integer, got {value[1]}"
        raise ValidationError(msg)

    if not isinstance(value[2], int):
        msg = f"Vector component Z is not an integer, got {value[2]}"
        raise ValidationError(msg)

    return f"{value[0]},{value[1]},{value[2]}"
