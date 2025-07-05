from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], extensions={"foo": "bar"}): ...
