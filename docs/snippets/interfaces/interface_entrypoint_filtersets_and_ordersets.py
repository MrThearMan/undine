from graphql import GraphQLNonNull, GraphQLString

from undine import Entrypoint, FilterSet, InterfaceField, InterfaceType, OrderSet, QueryType, RootType

from .models import Step, Task


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


class TaskFilterSet(FilterSet[Task]): ...


class TaskOrderSet(OrderSet[Task]): ...


class TaskType(QueryType[Task], interfaces=[Named], filterset=TaskFilterSet, orderset=TaskOrderSet): ...


class StepFilterSet(FilterSet[Step]): ...


class StepOrderSet(OrderSet[Step]): ...


class StepType(QueryType[Step], interfaces=[Named], filterset=StepFilterSet, orderset=StepOrderSet): ...


class Query(RootType):
    named = Entrypoint(Named, many=True)
