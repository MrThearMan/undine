from graphql import DirectiveLocation

from undine import Directive, Order, OrderSet

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.ENUM]): ...


class TaskOrderSet(OrderSet[Task], directives=[MyDirective()]):
    name = Order()
