from graphql import DirectiveLocation

from undine import Directive, OrderSet

from .models import Task


class NewDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="new"): ...


class TaskOrderSet(OrderSet[Task], directives=[NewDirective()]): ...


# Alternatively...


@NewDirective()
class TaskOrderSetAlt(OrderSet[Task]): ...
