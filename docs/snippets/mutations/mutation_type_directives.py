from graphql import DirectiveLocation

from undine import Input, MutationType
from undine.directives import Directive

from .models import Task


class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class TaskCreateMutation(MutationType[Task], directives=[MyDirective()]):
    name = Input()
