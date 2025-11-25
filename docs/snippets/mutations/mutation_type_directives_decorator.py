from graphql import DirectiveLocation

from undine import Input, MutationType
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT]): ...


@MyDirective()
class TaskCreateMutation(MutationType[Task]):
    name = Input()
