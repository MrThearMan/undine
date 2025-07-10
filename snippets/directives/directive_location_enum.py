from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import OrderSet
from undine.directives import Directive, DirectiveArgument

from .models import Task


class VersionDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class TaskOrderSet(OrderSet[Task], directives=[VersionDirective(value="v1.0.0")]): ...
