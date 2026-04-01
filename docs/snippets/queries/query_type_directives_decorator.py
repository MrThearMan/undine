from graphql import DirectiveLocation

from undine import Directive, Field, QueryType

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@MyDirective()
class TaskType(QueryType[Task]):
    name = Field()
