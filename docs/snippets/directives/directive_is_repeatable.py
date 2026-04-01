from graphql import DirectiveLocation

from undine import Directive, Entrypoint, RootType


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
