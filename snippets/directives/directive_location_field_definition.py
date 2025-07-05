from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Entrypoint, Field, InterfaceField, InterfaceType, QueryType, RootType
from undine.directives import Directive, DirectiveArgument

from .models import Task


class AddedInDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="addedIn"):
    version = DirectiveArgument(GraphQLNonNull(GraphQLString))


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString), directives=[AddedInDirective(version="v1.0.0")])


class TaskType(QueryType[Task], interfaces=[Named]):
    created_at = Field(directives=[AddedInDirective(version="v1.0.0")])


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True, directives=[AddedInDirective(version="v1.0.0")])
