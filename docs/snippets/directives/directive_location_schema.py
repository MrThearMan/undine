from graphql import DirectiveLocation

from undine import Entrypoint, RootType, create_schema
from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="new"): ...


class Query(RootType):
    @Entrypoint
    def example(self, value: str) -> str:
        return value


schema = create_schema(query=Query, schema_definition_directives=[NewDirective()])
