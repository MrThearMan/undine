from graphql import DirectiveLocation

from undine import Directive, FilterSet, MutationType

from .models import Task


class NewDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT], schema_name="new"): ...


class TaskFilterSet(FilterSet[Task], directives=[NewDirective()]): ...


class CreateTaskMutation(MutationType[Task], directives=[NewDirective()]): ...


# Alternatively...


@NewDirective()
class TaskFilterSetAlt(FilterSet[Task]): ...


@NewDirective()
class CreateTaskMutationAlt(MutationType[Task]): ...
