from graphql import DirectiveLocation

from undine import Directive, Field, QueryType

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class TaskType(QueryType[Task], directives=[MyDirective()]):
    name = Field()
