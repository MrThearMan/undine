from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.MUTATION], schema_name="new"): ...
