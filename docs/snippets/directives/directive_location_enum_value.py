from graphql import DirectiveLocation

from undine import Directive, Order, OrderSet

from .models import Task


class NewDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE], schema_name="new"): ...


class TaskOrderSet(OrderSet[Task]):
    name = Order("name", directives=[NewDirective()])

    # Alternatively...
    name_alt = Order("name") @ NewDirective()
