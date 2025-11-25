from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.FRAGMENT_SPREAD], schema_name="new"): ...
