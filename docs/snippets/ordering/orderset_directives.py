from graphql import DirectiveLocation

from undine import OrderSet
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.ENUM]): ...


class TaskOrderSet(OrderSet[Task], directives=[MyDirective()]): ...
