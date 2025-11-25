from graphql import DirectiveLocation

from undine import Filter, FilterSet, Input, MutationType
from undine.directives import Directive

from .models import Task


class NewDirective(Directive, locations=[DirectiveLocation.INPUT_FIELD_DEFINITION], schema_name="new"): ...


class TaskFilterSet(FilterSet[Task]):
    name = Filter(directives=[NewDirective()])

    # Alternatively...
    name_alt = Filter() @ NewDirective()


class CreateTaskMutation(MutationType[Task]):
    name = Input(directives=[NewDirective()])

    # Alternatively...
    name_alt = Input() @ NewDirective()
