from graphql import DirectiveLocation

from undine import Entrypoint, RootType
from undine.directives import Directive


class NewDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION],
    schema_name="new",
    is_repeatable=True,
): ...


class Query(RootType):
    @Entrypoint(directives=[NewDirective(), NewDirective()])
    def example(self) -> str:
        return "Example"

    # Alternatively...
    @NewDirective()
    @NewDirective()
    @Entrypoint()
    def example_alt(self) -> str:
        return "Example"
