from graphql import DirectiveLocation

from undine import Order, OrderSet
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.ENUM]): ...


@MyDirective()
class TaskOrderSet(OrderSet[Task]):
    name = Order()
