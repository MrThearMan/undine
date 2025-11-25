from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Entrypoint, Field, InterfaceField, InterfaceType, QueryType, RootType
from undine.directives import Directive

from .models import Task


class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="new"): ...


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString), directives=[NewDirective()])

    # Alternatively...
    name_alt = InterfaceField(GraphQLNonNull(GraphQLString)) @ NewDirective()


@Named
class TaskType(QueryType[Task]):
    created_at = Field(directives=[NewDirective()])

    # Alternatively...
    created_at_alt = Field() @ NewDirective()


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True, directives=[NewDirective()])

    # Alternatively...
    tasks_alt = Entrypoint(TaskType, many=True) @ NewDirective()
