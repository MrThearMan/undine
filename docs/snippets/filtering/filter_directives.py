from graphql import DirectiveLocation

from undine import Directive, Filter, FilterSet

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.INPUT_FIELD_DEFINITION]): ...


class TaskFilterSet(FilterSet[Task]):
    name = Filter(directives=[MyDirective()])
