from graphql import DirectiveLocation

from undine import Directive


class NewDirective(Directive, locations=[DirectiveLocation.QUERY], schema_name="new"): ...
