from graphql import DirectiveLocation

from undine import RootType
from undine.directives import Directive


class MyDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class Query(RootType, directives=[MyDirective()]): ...
