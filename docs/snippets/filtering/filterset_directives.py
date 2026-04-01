from graphql import DirectiveLocation

from undine import Directive, Filter, FilterSet

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT]): ...


class TaskFilterSet(FilterSet[Task], directives=[MyDirective()]):
    name = Filter()
