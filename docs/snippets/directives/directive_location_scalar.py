from graphql import DirectiveLocation

from undine.directives import Directive
from undine.scalars import ScalarType


class NewDirective(Directive, locations=[DirectiveLocation.SCALAR], schema_name="new"): ...


vector3_scalar = ScalarType(name="Vector3", directives=[NewDirective()])

# Alternatively...

vector3_scalar_alt = ScalarType(name="Vector3") @ NewDirective()
