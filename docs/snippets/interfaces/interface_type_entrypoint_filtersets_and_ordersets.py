from graphql import GraphQLNonNull, GraphQLString

from undine import Entrypoint, FilterSet, InterfaceField, InterfaceType, OrderSet, QueryType, RootType

from .models import Step, Task


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


class TaskFilterSet(FilterSet[Task]): ...


class TaskOrderSet(OrderSet[Task]): ...


@Named
@TaskFilterSet
@TaskOrderSet
class TaskType(QueryType[Task]): ...


class StepFilterSet(FilterSet[Step]): ...


class StepOrderSet(OrderSet[Step]): ...


@Named
@StepFilterSet
@StepOrderSet
class StepType(QueryType[Step]): ...


class Query(RootType):
    named = Entrypoint(Named, many=True)
