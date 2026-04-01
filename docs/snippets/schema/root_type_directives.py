from graphql import DirectiveLocation

from undine import Directive, Entrypoint, RootType


class MyDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


class Query(RootType, directives=[MyDirective()]):
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"
