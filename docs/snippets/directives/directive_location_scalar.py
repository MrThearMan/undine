from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine.directives import Directive, DirectiveArgument
from undine.scalars import ScalarType


class VersionDirective(Directive, locations=[DirectiveLocation.SCALAR], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


Vector3 = tuple[int, int, int]

vector3_scalar: ScalarType[Vector3, str] = ScalarType(
    name="Vector3",
    description="Represents a 3D vector as a string in format 'X,Y,Z'.",
    directives=[VersionDirective(value="v1.0.0")],
)
