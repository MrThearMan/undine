from undine import Entrypoint, FilterSet, OrderSet, QueryType, RootType, UnionType

from .models import Project, Task


class TaskFilterSet(FilterSet[Task]): ...


class TaskOrderSet(OrderSet[Task]): ...


@TaskFilterSet
@TaskOrderSet
class TaskType(QueryType[Task]): ...


class ProjectFilterSet(FilterSet[Project]): ...


class ProjectOrderSet(OrderSet[Project]): ...


@ProjectFilterSet
@ProjectOrderSet
class ProjectType(QueryType[Project]): ...


class SearchObjects(UnionType[TaskType, ProjectType]): ...


class Query(RootType):
    search_objects = Entrypoint(SearchObjects, many=True)
