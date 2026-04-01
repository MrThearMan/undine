from graphql import DirectiveLocation

from undine import Directive, Field, QueryType

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class TaskType(QueryType[Task]):
    name = Field() @ MyDirective()
