from django.db.models import CharField, Value
from django.db.models.functions import Concat, Upper
from graphql import GraphQLNonNull, GraphQLString

from undine import Field, InterfaceField, InterfaceType, QueryType

from .models import Step, Task


class Named(InterfaceType):
    display_name = InterfaceField(GraphQLNonNull(GraphQLString))


class TaskType(QueryType[Task], interfaces=[Named]):
    display_name = Field(Concat("name", Value(" (task)"), output_field=CharField()))


class StepType(QueryType[Step], interfaces=[Named]):
    display_name = Field(Upper("name"))
