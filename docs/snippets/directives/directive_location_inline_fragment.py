from graphql import DirectiveLocation

from undine import Directive


class NewDirective(Directive, locations=[DirectiveLocation.INLINE_FRAGMENT], schema_name="new"): ...
