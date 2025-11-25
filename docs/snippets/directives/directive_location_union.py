from graphql import DirectiveLocation

from undine import QueryType, UnionType
from undine.directives import Directive

from .models import Project, Task


class NewDirective(Directive, locations=[DirectiveLocation.UNION], schema_name="new"): ...


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class SearchObject(UnionType[TaskType, ProjectType], directives=[NewDirective()]): ...


# Alternatively...


@NewDirective()
class SearchObjectAlt(UnionType[TaskType, ProjectType]): ...
