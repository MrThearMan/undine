from graphql import DirectiveLocation

from undine import Field, QueryType
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@MyDirective()
class TaskType(QueryType[Task]):
    name = Field()
