from graphql import DirectiveLocation

from undine import Directive


class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="new"): ...
