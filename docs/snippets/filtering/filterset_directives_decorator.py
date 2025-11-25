from graphql import DirectiveLocation

from undine import Filter, FilterSet
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT]): ...


@MyDirective()
class TaskFilterSet(FilterSet[Task]):
    name = Filter()
