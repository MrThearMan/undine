from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Filter, FilterSet, Input, MutationType
from undine.directives import Directive, DirectiveArgument

from .models import Task


class AddedInDirective(Directive, locations=[DirectiveLocation.INPUT_FIELD_DEFINITION], schema_name="addedIn"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class TaskFilterSet(FilterSet[Task]):
    name = Filter(directives=[AddedInDirective(value="v1.0.0")])


class CreateTaskMutation(MutationType[Task]):
    name = Input(directives=[AddedInDirective(value="v1.0.0")])
