from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.VARIABLE_DEFINITION], schema_name="new"): ...
