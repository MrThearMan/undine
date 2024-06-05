from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Order, OrderSet
from undine.directives import Directive, DirectiveArgument

from .models import Task


class AddedInDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE], schema_name="addedIn"):
    version = DirectiveArgument(GraphQLNonNull(GraphQLString))


class TaskOrderSet(OrderSet[Task]):
    name = Order("name", directives=[AddedInDirective(version="v1.0.0")])
