from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import FilterSet, MutationType
from undine.directives import Directive, DirectiveArgument

from .models import Task


class VersionDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class TaskFilterSet(FilterSet[Task], directives=[VersionDirective(value="v1.0.0")]): ...


class CreateTaskMutation(MutationType[Task], directives=[VersionDirective(value="v1.0.0")]): ...
