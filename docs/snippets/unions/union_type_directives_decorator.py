from graphql import DirectiveLocation

from undine import Directive, QueryType, UnionType

from .models import Project, Task


class MyDirective(Directive, locations=[DirectiveLocation.UNION]): ...


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


@MyDirective()
class SearchObjects(UnionType[TaskType, ProjectType]): ...
