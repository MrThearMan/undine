from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.QUERY], schema_name="new"): ...
