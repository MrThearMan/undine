from graphql import DirectiveLocation

from undine import OrderSet
from undine.directives import Directive

from .models import Task


class NewDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="new"): ...


class TaskOrderSet(OrderSet[Task], directives=[NewDirective()]): ...


# Alternatively...


@NewDirective()
class TaskOrderSetAlt(OrderSet[Task]): ...
