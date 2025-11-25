from graphql import DirectiveLocation

from undine import FilterSet, MutationType
from undine.directives import Directive

from .models import Task


class NewDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT], schema_name="new"): ...


class TaskFilterSet(FilterSet[Task], directives=[NewDirective()]): ...


class CreateTaskMutation(MutationType[Task], directives=[NewDirective()]): ...


# Alternatively...


@NewDirective()
class TaskFilterSetAlt(FilterSet[Task]): ...


@NewDirective()
class CreateTaskMutationAlt(MutationType[Task]): ...
