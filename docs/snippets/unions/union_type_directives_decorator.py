from graphql import DirectiveLocation

from undine import QueryType, UnionType
from undine.directives import Directive

from .models import Project, Task


class MyDirective(Directive, locations=[DirectiveLocation.UNION]): ...


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


@MyDirective()
class SearchObjects(UnionType[TaskType, ProjectType]): ...
