from graphql import DirectiveLocation

from undine import Directive, Filter, FilterSet

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT]): ...


@MyDirective()
class TaskFilterSet(FilterSet[Task]):
    name = Filter()
