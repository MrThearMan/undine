from undine import Entrypoint, FilterSet, OrderSet, QueryType, RootType, UnionType

from .models import Project, Task


class TaskFilterSet(FilterSet[Task]): ...


class TaskOrderSet(OrderSet[Task]): ...


class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet): ...


class ProjectFilterSet(FilterSet[Project]): ...


class ProjectOrderSet(OrderSet[Project]): ...


class ProjectType(QueryType[Project], filterset=ProjectFilterSet, orderset=ProjectOrderSet): ...


class SearchObjects(UnionType[TaskType, ProjectType]): ...


class Query(RootType):
    search_objects = Entrypoint(SearchObjects, many=True)
