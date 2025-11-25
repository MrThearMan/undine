from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.SUBSCRIPTION], schema_name="new"): ...
