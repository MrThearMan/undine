from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="new"): ...
