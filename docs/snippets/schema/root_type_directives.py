from graphql import DirectiveLocation

from undine import Entrypoint, RootType
from undine.directives import Directive


class MyDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class Query(RootType, directives=[MyDirective()]):
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"
