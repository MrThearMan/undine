from graphql import DirectiveLocation

from undine import QueryType
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class TaskType(QueryType[Task], directives=[MyDirective()]): ...
