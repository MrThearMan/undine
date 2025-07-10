from graphql import DirectiveLocation

from undine import Entrypoint, QueryType, RootType
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class TaskType(QueryType[Task]): ...


class Query(RootType):
    task = Entrypoint(TaskType, directives=[MyDirective()])
