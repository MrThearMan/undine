from graphql import DirectiveLocation

from undine import Directive, Entrypoint, RootType, create_schema


class NewDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="new"): ...


class Query(RootType):
    @Entrypoint
    def example(self, value: str) -> str:
        return value


schema = create_schema(query=Query, schema_definition_directives=[NewDirective()])
