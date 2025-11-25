from graphql import DirectiveLocation

from undine import Entrypoint, QueryType, RootType
from undine.directives import Directive

from .models import Task


class NewDirective(Directive, locations=[DirectiveLocation.OBJECT], schema_name="new"): ...


class TaskType(QueryType[Task], directives=[NewDirective()]): ...


class Query(RootType, directives=[NewDirective()]):
    tasks = Entrypoint(TaskType, many=True)


# Alternatively...


@NewDirective()
class TaskTypeAlt(QueryType[Task]): ...


@NewDirective()
class QueryAlt(RootType):
    tasks = Entrypoint(TaskType, many=True)
