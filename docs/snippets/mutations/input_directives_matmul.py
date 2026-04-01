from graphql import DirectiveLocation

from undine import Directive, Input, MutationType

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.INPUT_FIELD_DEFINITION]): ...


class TaskCreateMutation(MutationType[Task]):
    name = Input() @ MyDirective()
