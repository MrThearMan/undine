from django.db.models import Value
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Calculation, CalculationArgument, DjangoExpression, GQLInfo
from undine.directives import Directive, DirectiveArgument


class NewDirective(Directive, locations=[DirectiveLocation.ARGUMENT_DEFINITION], schema_name="new"): ...


class VersionDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString), directives=[NewDirective()])

    # Alternatively...
    value_alt = DirectiveArgument(GraphQLNonNull(GraphQLString)) @ NewDirective()


class Calc(Calculation[int]):
    value = CalculationArgument(int, directives=[NewDirective()])

    # Alternatively...
    value_alt = CalculationArgument(int) @ NewDirective()

    def __call__(self, info: GQLInfo) -> DjangoExpression:
        return Value(self.value)
