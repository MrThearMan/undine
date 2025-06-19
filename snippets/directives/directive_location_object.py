from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Entrypoint, QueryType, RootType
from undine.directives import Directive, DirectiveArgument

from .models import Task


class VersionDirective(Directive, locations=[DirectiveLocation.OBJECT], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class TaskType(QueryType[Task], directives=[VersionDirective(value="v1.0.0")]): ...


class Query(RootType, directives=[VersionDirective(value="v2.0.0")]):
    tasks = Entrypoint(TaskType, many=True)
