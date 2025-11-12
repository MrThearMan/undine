from graphql import DirectiveLocation

from undine import Order, OrderSet
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE]): ...


class TaskOrderSet(OrderSet[Task]):
    name = Order() @ MyDirective()
