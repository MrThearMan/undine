from graphql import GraphQLNonNull, GraphQLString

from undine import Entrypoint, Filter, FilterSet, InterfaceField, InterfaceType, Order, OrderSet, QueryType, RootType

from .models import Step, Task


class NamedFilterSet(FilterSet[Task, Step], auto=False):
    name = Filter()
    name_contains = Filter(lookup="icontains", field_name="name")


class NamedOrderSet(OrderSet[Task, Step], auto=False):
    name = Order()


@NamedFilterSet
@NamedOrderSet
class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


@Named
class TaskType(QueryType[Task]): ...


@Named
class StepType(QueryType[Step]): ...


class Query(RootType):
    named = Entrypoint(Named, many=True)
