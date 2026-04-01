from graphql import DirectiveLocation

from undine import Directive, Input, MutationType

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT]): ...


@MyDirective()
class TaskCreateMutation(MutationType[Task]):
    name = Input()
