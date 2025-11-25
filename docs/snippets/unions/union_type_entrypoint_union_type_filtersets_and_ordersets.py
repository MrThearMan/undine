from undine import Entrypoint, FilterSet, OrderSet, QueryType, RootType, UnionType

from .models import Project, Task


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class SearchObjectsFilterSet(FilterSet[Task, Project]): ...


class SearchObjectsOrderSet(OrderSet[Task, Project]): ...


@SearchObjectsFilterSet
@SearchObjectsOrderSet
class SearchObjects(UnionType[TaskType, ProjectType]): ...


class Query(RootType):
    search_objects = Entrypoint(SearchObjects, many=True)
