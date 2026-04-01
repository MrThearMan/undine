from graphql import DirectiveLocation

from undine import Directive


class NewDirective(Directive, locations=[DirectiveLocation.MUTATION], schema_name="new"): ...
