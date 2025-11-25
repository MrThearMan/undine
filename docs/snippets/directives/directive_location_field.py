from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.FIELD], schema_name="new"): ...
