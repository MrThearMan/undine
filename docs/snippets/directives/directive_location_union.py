from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import QueryType, UnionType
from undine.directives import Directive, DirectiveArgument

from .models import Project, Task


class VersionDirective(Directive, locations=[DirectiveLocation.UNION], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class SearchObject(UnionType[TaskType, ProjectType], directives=[VersionDirective(value="v1.0.0")]): ...
