from graphql import DirectiveLocation

from undine import Directive, Order, OrderSet

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE]): ...


class TaskOrderSet(OrderSet[Task]):
    name = Order() @ MyDirective()
