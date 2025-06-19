from graphql import DirectiveLocation

from undine import FilterSet
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT]): ...


class TaskFilterSet(FilterSet[Task], directives=[MyDirective()]): ...
