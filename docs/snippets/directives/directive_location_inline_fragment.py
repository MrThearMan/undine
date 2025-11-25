from graphql import DirectiveLocation

from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.INLINE_FRAGMENT], schema_name="new"): ...
