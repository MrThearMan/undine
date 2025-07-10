from django.db.models import Value
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Calculation, CalculationArgument, DjangoExpression, GQLInfo
from undine.directives import Directive, DirectiveArgument


# Actual directive can be defined in multiple locations, but omit those for brevity.
class AddedInDirective(Directive, locations=[DirectiveLocation.ARGUMENT_DEFINITION], schema_name="addedIn"):
    version = DirectiveArgument(GraphQLNonNull(GraphQLString))


class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="new"):
    version = DirectiveArgument(
        GraphQLNonNull(GraphQLString),
        directives=[AddedInDirective(version="v1.0.0")],
    )


class Calc(Calculation[int]):
    value = CalculationArgument(int, directives=[AddedInDirective(version="v1.0.0")])

    def __call__(self, info: GQLInfo) -> DjangoExpression:
        return Value(self.value)
