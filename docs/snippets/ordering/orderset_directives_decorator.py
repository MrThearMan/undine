from graphql import DirectiveLocation

from undine import Directive, Order, OrderSet

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.ENUM]): ...


@MyDirective()
class TaskOrderSet(OrderSet[Task]):
    name = Order()
