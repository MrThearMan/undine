from graphql import DirectiveLocation

from undine import Directive


class NewDirective(Directive, locations=[DirectiveLocation.FRAGMENT_SPREAD], schema_name="new"): ...
