from graphql import DirectiveLocation

from undine import Directive, Entrypoint, RootType


class MyDirective(Directive, locations=[DirectiveLocation.OBJECT]): ...


@MyDirective()
class Query(RootType):
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"
